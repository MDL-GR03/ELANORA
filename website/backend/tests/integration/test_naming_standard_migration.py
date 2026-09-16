"""Copying legacy upload naming standards into protocol drafts.

Naming standards are mutable settings, so they cannot show which rules accepted
an old revision. The copy puts each project's current upload standard into a
draft an administrator reviews and publishes. Nothing is published or pinned,
and the legacy settings stay as they are.
"""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.effective_naming_standard_locations import get_location_id_by_name
from app.model.accepted_value import AcceptedValue
from app.model.audit_event import AuditEvent
from app.model.component_template import ComponentTemplate
from app.model.effective_naming_standard import EffectiveNamingStandard
from app.model.enums import ProtocolVersionStatus, UserRole
from app.model.file_type import FileType
from app.model.instance import Instance
from app.model.project import Project
from app.model.project_file_type import ProjectFileType
from app.model.project_naming_standard import ProjectNamingStandard
from app.model.protocol import Protocol, ProtocolVersion
from app.model.standard_component import StandardComponent
from app.model.user import User
from app.schema.protocol import ProtocolRules
from app.service.naming_standard_migration import (
    copy_naming_standards_into_protocol_drafts,
)
from app.service.protocol_administration import (
    create_protocol,
    pin_protocol_version,
    publish_protocol_version,
)

EXPECTED_STANDARD = {
    "name": "Session files",
    "pattern": "{corpus}_{session}",
    "components": [
        {"name": "corpus", "regex": "[A-Z]+", "accepted_values": ["LSFB"]},
        {"name": "session", "regex": "[0-9]+", "accepted_values": ["001-120"]},
    ],
}


async def _institution(session: AsyncSession) -> tuple[Instance, User]:
    instance = Instance(
        instance_name="Naming Lab",
        institution_name="Naming Institute",
        contact_email="admin@naming.example",
        domain="naming.example",
        timezone="UTC",
    )
    admin = User(
        username="naming-admin",
        email="admin@naming.example",
        hashed_password="fixture",  # noqa: S106
        first_name="Ada",
        last_name="Admin",
        affiliation="Institute",
        department="Research IT",
        activation_code="fixture",
        is_verified_account=True,
        role=UserRole.ADMIN,
        instance=instance,
    )
    session.add_all([instance, admin])
    await session.flush()
    return instance, admin


async def _project(
    session: AsyncSession,
    instance: Instance,
    name: str,
    *,
    pattern: str = "{corpus}_{session}",
    location: str = "uploadPage",
) -> Project:
    project = Project(
        project_name=name, project_path=name, instance_id=instance.instance_id
    )
    file_type = await session.scalar(
        select(FileType).where(FileType.extension == "eaf")
    )
    if file_type is None:
        file_type = FileType(extension="eaf")
    session.add_all([project, file_type])
    await session.flush()
    project_file_type = ProjectFileType(
        project_id=project.project_id, file_type_id=file_type.id, name="ELAN"
    )
    standard = ProjectNamingStandard(
        project_id=project.project_id,
        name="Session files",
        project_file_type=project_file_type,
        pattern=pattern,
        description="Legacy setting",
    )
    session.add_all([project_file_type, standard])
    await session.flush()
    for order, (component, regex, value) in enumerate(
        [("corpus", "[A-Z]+", "LSFB"), ("session", "[0-9]+", "001-120")]
    ):
        template = await session.scalar(
            select(ComponentTemplate).where(ComponentTemplate.name == component)
        )
        if template is None:
            template = ComponentTemplate(
                file_type_id=file_type.id, name=component, regex=regex
            )
            template.accepted_values.append(AcceptedValue(value=value))
            session.add(template)
            await session.flush()
        session.add(
            StandardComponent(
                naming_standard_id=standard.id,
                component_template_id=template.id,
                order=order,
            )
        )
    session.add(
        EffectiveNamingStandard(
            project_id=project.project_id,
            project_file_type_id=project_file_type.id,
            naming_standard_id=standard.id,
            location_id=get_location_id_by_name(location),
        )
    )
    await session.flush()
    return project


async def _drafts(session: AsyncSession) -> list[ProtocolVersion]:
    return list(
        (
            await session.scalars(
                select(ProtocolVersion)
                .where(ProtocolVersion.status == ProtocolVersionStatus.DRAFT)
                .order_by(ProtocolVersion.created_at)
            )
        ).all()
    )


@pytest.mark.asyncio
async def test_a_project_without_a_protocol_gets_a_new_draft(
    session: AsyncSession,
) -> None:
    instance, _ = await _institution(session)
    project = await _project(session, instance, "sessions")
    project_id = project.project_id

    report = await copy_naming_standards_into_protocol_drafts(session)

    (draft,) = await _drafts(session)
    assert draft.rules["filename_standard"] == EXPECTED_STANDARD
    protocol = await session.get(Protocol, draft.protocol_id)
    assert protocol is not None
    assert protocol.name == "sessions filename standard"
    assert [item["project_id"] for item in report.copied] == [project_id]
    assert project.protocol_version_id is None
    assert (
        await session.scalar(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.action == "protocol.naming_standard.copied")
        )
        == 1
    )


@pytest.mark.asyncio
async def test_a_pinned_protocol_gets_its_next_draft_with_rules_kept(
    session: AsyncSession,
) -> None:
    instance, admin = await _institution(session)
    project = await _project(session, instance, "pinned")
    protocol = await create_protocol(
        session,
        project=project,
        name="Corpus protocol",
        description=None,
        rules=ProtocolRules(required_tiers=["utterance"]),
        actor_user_id=admin.user_id,
    )
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=protocol.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    await pin_protocol_version(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=admin.user_id,
    )

    await copy_naming_standards_into_protocol_drafts(session)

    (draft,) = await _drafts(session)
    assert draft.protocol_id == protocol.protocol_id
    assert draft.version_number == 2
    assert draft.rules["required_tiers"] == ["utterance"]
    assert draft.rules["filename_standard"] == EXPECTED_STANDARD
    # The project keeps enforcing the published version until someone pins.
    assert project.protocol_version_id == published.protocol_version_id


@pytest.mark.asyncio
async def test_running_the_copy_twice_creates_nothing_more(
    session: AsyncSession,
) -> None:
    instance, _ = await _institution(session)
    await _project(session, instance, "twice")

    await copy_naming_standards_into_protocol_drafts(session)
    again = await copy_naming_standards_into_protocol_drafts(session)

    assert len(await _drafts(session)) == 1
    assert again.copied == []
    assert [item["reason"] for item in again.skipped] == ["already_copied"]


@pytest.mark.asyncio
async def test_unusable_and_non_upload_standards_are_not_copied(
    session: AsyncSession,
) -> None:
    instance, _ = await _institution(session)
    await _project(session, instance, "broken", pattern="{corpus}")
    await _project(session, instance, "tiers-only", location="tiers")

    report = await copy_naming_standards_into_protocol_drafts(session)

    assert await _drafts(session) == []
    assert [(item["project_name"], item["reason"]) for item in report.skipped] == [
        ("broken", "unusable_standard")
    ]


@pytest.mark.asyncio
async def test_a_dry_run_reports_without_writing(session: AsyncSession) -> None:
    instance, _ = await _institution(session)
    await _project(session, instance, "preview")

    report = await copy_naming_standards_into_protocol_drafts(session, dry_run=True)

    assert [item["project_name"] for item in report.copied] == ["preview"]
    assert await _drafts(session) == []
