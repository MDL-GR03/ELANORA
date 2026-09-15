"""Purging a deleted project's content once its retention period ends.

A purge removes the research content itself: files, revisions, manifests,
contributions, reviews and rejected uploads, and the project's Git export. The
project row stays as a tombstone, and the audit trail records what went, so the
institution can still show that the data existed and when it was destroyed.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from conftest import GIT, PROJECT, Browser, InstitutionAccounts, project_with_member
from httpx import AsyncClient
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.project_revision import ProjectRevision
from app.service.retention_purge import (
    purge_expired_projects,
    purgeable_projects,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


async def _accepted_project(browser: Browser, accounts: InstitutionAccounts) -> int:
    project_id = await project_with_member(browser, accounts)
    uploaded = await browser.upload(project_id, "session-001.eaf", FIXTURE.read_bytes())
    assert uploaded.status_code == 200, uploaded.text
    pending = await browser.get(f"{GIT}/projects/{PROJECT}/admin/pending-uploads")
    (contribution,) = pending.json()["pending_uploads"]
    accepted = await browser.post(
        f"{GIT}/projects/{PROJECT}/admin/pending-uploads/"
        f"{contribution['branch_name']}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert accepted.status_code == 200, accepted.text
    return project_id


async def _deleted_long_ago(
    session: AsyncSession,
    project_id: int,
    *,
    retention_days: int | None,
    days_since_deletion: int,
    legal_hold: bool = False,
) -> Project:
    project = await session.get(Project, project_id)
    assert project is not None
    project.deleted_at = datetime.now(UTC) - timedelta(days=days_since_deletion)
    project.retention_days = retention_days
    project.legal_hold = legal_hold
    project.legal_hold_reason = "Ongoing audit" if legal_hold else None
    await session.commit()
    return project


async def _content_counts(session: AsyncSession, project_id: int) -> dict[str, int]:
    async def count(statement) -> int:
        return int(await session.scalar(statement) or 0)

    files = (
        select(func.count())
        .select_from(ElanFile)
        .where(ElanFile.project_id == project_id)
    )
    revisions = (
        select(func.count())
        .select_from(EafRevision)
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project_id)
    )
    manifests = (
        select(func.count())
        .select_from(ProjectRevision)
        .where(ProjectRevision.project_id == project_id)
    )
    uploads = (
        select(func.count())
        .select_from(PendingUpload)
        .where(PendingUpload.project_id == project_id)
    )
    return {
        "files": await count(files),
        "revisions": await count(revisions),
        "manifests": await count(manifests),
        "uploads": await count(uploads),
    }


@pytest.mark.asyncio
async def test_expired_content_is_purged_while_the_tombstone_remains(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    browser = Browser(api_client)
    project_id = await _accepted_project(browser, institution_accounts)
    await _deleted_long_ago(
        session, project_id, retention_days=30, days_since_deletion=31
    )
    project_path = tmp_path / "projects" / PROJECT
    assert project_path.is_dir()
    before = await _content_counts(session, project_id)
    # Creating the project records a manifest, and accepting the file another.
    assert before["files"] == 1
    assert before["revisions"] == 1
    assert before["manifests"] >= 1
    assert before["uploads"] == 1

    report = await purge_expired_projects(session)
    await session.commit()

    assert [item["project_id"] for item in report.purged] == [project_id]
    assert await _content_counts(session, project_id) == {
        "files": 0,
        "revisions": 0,
        "manifests": 0,
        "uploads": 0,
    }
    assert not project_path.exists()
    session.expire_all()
    tombstone = await session.get(Project, project_id)
    assert tombstone is not None
    assert tombstone.project_name == PROJECT
    assert tombstone.content_purged_at is not None
    assert tombstone.current_revision_id is None
    event = await session.scalar(
        select(AuditEvent).where(AuditEvent.action == "project.content.purged")
    )
    assert event is not None
    assert event.details["files"] == 1
    assert event.details["revisions"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("retention_days", "days_since_deletion", "legal_hold", "reason"),
    [
        (30, 10, False, "the retention period has not ended"),
        (None, 900, False, "no retention period is set"),
        (30, 400, True, "a legal hold is in place"),
    ],
)
async def test_content_is_kept_until_it_is_really_due(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
    retention_days: int | None,
    days_since_deletion: int,
    legal_hold: bool,
    reason: str,
) -> None:
    browser = Browser(api_client)
    project_id = await _accepted_project(browser, institution_accounts)
    await _deleted_long_ago(
        session,
        project_id,
        retention_days=retention_days,
        days_since_deletion=days_since_deletion,
        legal_hold=legal_hold,
    )

    assert await purgeable_projects(session) == [], reason
    report = await purge_expired_projects(session)

    assert report.purged == []
    assert (await _content_counts(session, project_id))["files"] == 1


@pytest.mark.asyncio
async def test_a_project_still_in_use_is_never_purged(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    """Only deleted projects are purged, however old their retention period."""
    browser = Browser(api_client)
    project_id = await _accepted_project(browser, institution_accounts)
    project = await session.get(Project, project_id)
    assert project is not None
    project.retention_days = 30
    await session.commit()

    assert await purgeable_projects(session) == []
    assert (await _content_counts(session, project_id))["files"] == 1


@pytest.mark.asyncio
async def test_a_dry_run_reports_without_destroying_anything(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
    tmp_path: Path,
) -> None:
    browser = Browser(api_client)
    project_id = await _accepted_project(browser, institution_accounts)
    await _deleted_long_ago(
        session, project_id, retention_days=30, days_since_deletion=90
    )

    report = await purge_expired_projects(session, dry_run=True)

    assert [item["project_id"] for item in report.purged] == [project_id]
    assert (await _content_counts(session, project_id))["files"] == 1
    assert (tmp_path / "projects" / PROJECT).is_dir()


async def _validated_project(
    browser: Browser, accounts: InstitutionAccounts, session: AsyncSession
) -> int:
    """An accepted file, a published pinned protocol and a validation run."""
    project_id = await _accepted_project(browser, accounts)
    protocol = await browser.post(
        f"/api/v1/projects/{project_id}/protocols",
        # A missing tier, so the run records an issue as well.
        json={"name": "Guarded", "rules": {"required_tiers": ["gloss", "utterance"]}},
    )
    version_id = protocol.json()["versions"][0]["protocol_version_id"]
    await browser.post(
        f"/api/v1/projects/{project_id}/protocol-versions/{version_id}/publish"
    )
    await browser.put(f"/api/v1/projects/{project_id}/protocol-version/{version_id}")
    revision_id = await session.scalar(
        select(EafRevision.revision_id)
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project_id)
    )
    session.expire_all()
    probe = await session.get(Project, project_id)
    print("PINNED", probe.protocol_version_id, "REVISION", revision_id)
    run = await browser.post(
        f"/api/v1/projects/{project_id}/revisions/{revision_id}/validations"
    )
    assert run.status_code == 200, run.text
    return project_id


@pytest.mark.asyncio
async def test_immutable_rows_refuse_deletion_outside_a_purge(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    """The guards read an unset session setting as "not purging".

    They compared current_setting(..., true) with 'on'. When the setting was
    absent, which is every ordinary transaction, the comparison was NULL and
    the guard never raised, so these rows could be deleted by anything holding
    a database session.
    """
    browser = Browser(api_client)
    await _validated_project(browser, institution_accounts, session)

    for table, message in (
        ('"PROJECT_REVISION_EAF"', "PROJECT_REVISION_EAF is append-only"),
        ('"PROJECT_REVISION"', "PROJECT_REVISION is append-only"),
        ('"VALIDATION_ISSUE"', "validation evidence is immutable"),
        ('"VALIDATION_RUN"', "validation evidence is immutable"),
        ('"VALIDATOR_RELEASE"', "validation evidence is immutable"),
        ('"PROTOCOL_VERSION"', "published protocol versions are immutable"),
    ):
        rows = await session.scalar(text(f"SELECT count(*) FROM {table}"))  # noqa: S608
        assert rows, f"{table} needs a row for this check to mean anything"
        with pytest.raises(Exception, match=message):
            await session.execute(text(f"DELETE FROM {table}"))  # noqa: S608
        await session.rollback()


@pytest.mark.asyncio
async def test_the_ledger_stays_append_only_outside_a_purge(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    """The purge is the only way revision history may be removed."""
    browser = Browser(api_client)
    project_id = await _accepted_project(browser, institution_accounts)

    rows = await session.scalar(
        text(
            'SELECT count(*) FROM "PROJECT_REVISION_EAF" WHERE project_revision_id IN '
            '(SELECT revision_id FROM "PROJECT_REVISION" WHERE project_id = :id)'
        ),
        {"id": project_id},
    )
    assert rows, "the accepted file must appear in a revision manifest"

    with pytest.raises(Exception, match="PROJECT_REVISION_EAF is append-only"):
        await session.execute(
            text(
                'DELETE FROM "PROJECT_REVISION_EAF" WHERE project_revision_id IN '
                '(SELECT revision_id FROM "PROJECT_REVISION" WHERE project_id = :id)'
            ),
            {"id": project_id},
        )
    await session.rollback()
    remaining = await session.scalar(
        select(func.count())
        .select_from(ProjectRevision)
        .where(ProjectRevision.project_id == project_id)
    )
    assert remaining
