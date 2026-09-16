"""Getting the audit trail out, for the questions an institution must answer.

Classification and retention exist so an institution can show an ethics board
or a data protection authority what it held, why, and when it destroyed it.
That evidence is only useful if it can leave the system in a form someone can
read and file.
"""

import csv
import io
import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent
from app.model.instance import Instance
from app.model.project import Project
from app.service.audit_export import export_audit_events

NOW = datetime.now(UTC)


async def _events(session: AsyncSession) -> tuple[int, int]:
    """Two projects with a trail between them, as an institution would have."""
    institution = Instance(
        instance_name="Audit Lab",
        institution_name="Audit Institute",
        contact_email="admin@audit.example",
        domain="audit.example",
        timezone="UTC",
    )
    session.add(institution)
    await session.flush()
    first = Project(
        project_name="first", project_path="first", instance_id=institution.instance_id
    )
    second = Project(
        project_name="second",
        project_path="second",
        instance_id=institution.instance_id,
    )
    session.add_all([first, second])
    await session.flush()
    session.add_all(
        [
            AuditEvent(
                actor_user_id=None,
                project_id=first.project_id,
                action="project.content.purged",
                resource_type="project",
                resource_id="1",
                details={"files": 3},
                occurred_at=NOW - timedelta(days=10),
            ),
            AuditEvent(
                actor_user_id=None,
                project_id=second.project_id,
                action="project.data_governance.updated",
                resource_type="project",
                resource_id="2",
                details={"after": {"data_classification": "sensitive_personal"}},
                occurred_at=NOW - timedelta(days=2),
            ),
            AuditEvent(
                actor_user_id=None,
                project_id=first.project_id,
                action="protocol.version.published",
                resource_type="protocol_version",
                resource_id="abc",
                details={},
                occurred_at=NOW - timedelta(hours=1),
            ),
        ]
    )
    await session.commit()
    return first.project_id, second.project_id


@pytest.mark.asyncio
async def test_everything_recorded_can_be_exported_as_json(
    session: AsyncSession,
) -> None:
    await _events(session)
    output = io.StringIO()

    count = await export_audit_events(session, output, output_format="json")

    exported = json.loads(output.getvalue())
    assert count == 3
    assert {item["action"] for item in exported} == {
        "project.content.purged",
        "project.data_governance.updated",
        "protocol.version.published",
    }
    purge = next(i for i in exported if i["action"] == "project.content.purged")
    assert purge["details"]["files"] == 3
    assert purge["occurred_at"].endswith("+00:00"), "an instant, not a local time"


@pytest.mark.asyncio
async def test_it_exports_as_csv_for_the_people_who_file_it(
    session: AsyncSession,
) -> None:
    await _events(session)
    output = io.StringIO()

    await export_audit_events(session, output, output_format="csv")

    rows = list(csv.DictReader(io.StringIO(output.getvalue())))
    assert len(rows) == 3
    assert {"occurred_at", "action", "project_id", "details"} <= set(rows[0])


@pytest.mark.asyncio
async def test_a_request_about_one_project_does_not_export_another(
    session: AsyncSession,
) -> None:
    await _events(session)
    output = io.StringIO()

    count = await export_audit_events(
        session, output, project_id=2, output_format="json"
    )

    assert count == 1
    assert json.loads(output.getvalue())[0]["project_id"] == 2


@pytest.mark.asyncio
async def test_a_period_can_be_asked_for(session: AsyncSession) -> None:
    """Requests are usually about a window, not the whole history."""
    await _events(session)
    output = io.StringIO()

    count = await export_audit_events(
        session, output, since=NOW - timedelta(days=5), output_format="json"
    )

    assert count == 2
    assert all(
        datetime.fromisoformat(item["occurred_at"]) >= NOW - timedelta(days=5)
        for item in json.loads(output.getvalue())
    )


@pytest.mark.asyncio
async def test_an_empty_period_exports_nothing_rather_than_failing(
    session: AsyncSession,
) -> None:
    await _events(session)
    output = io.StringIO()

    count = await export_audit_events(
        session, output, since=NOW + timedelta(days=1), output_format="json"
    )

    assert count == 0
    assert json.loads(output.getvalue()) == []


@pytest.mark.asyncio
async def test_events_are_exported_oldest_first(session: AsyncSession) -> None:
    """A trail read out of order is hard to reason about."""
    await _events(session)
    output = io.StringIO()

    await export_audit_events(session, output, output_format="json")

    moments = [item["occurred_at"] for item in json.loads(output.getvalue())]
    assert moments == sorted(moments)
