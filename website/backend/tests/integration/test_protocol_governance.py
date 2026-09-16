"""PostgreSQL scenarios for protocol permissions and immutable evidence."""

from io import BytesIO
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError
from app.crud.association import get_project_users
from app.crud.eaf_revision import append_eaf_revision
from app.dependency.elan_validation import validate_and_record_elan_files
from app.elan import parse_eaf
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_ingestion_attempt import EafIngestionAttempt
from app.model.elan_file import ElanFile
from app.model.enums import (
    ProjectCapability,
    ProjectPermission,
    ProtocolVersionStatus,
    UserRole,
    ValidationOutcome,
    ValidationSeverity,
)
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.model.protocol import ProjectComplianceScan, ProtocolVersion, ValidationRun
from app.model.user import User
from app.schema.protocol import ProtocolRules
from app.schema.review import ReviewCaseCreate
from app.service.protocol_administration import (
    archive_protocol_version,
    create_protocol,
    delete_protocol_draft,
    pin_protocol_version,
    publish_protocol_version,
    purge_archived_protocol_version,
    update_draft,
)
from app.service.protocol_capabilities import grant_protocol_manager
from app.service.protocol_compliance import (
    compliance_scan_response,
    list_compliance_scans,
    run_compliance_scan,
)
from app.service.protocol_errors import ProtocolConflictError
from app.service.protocol_suggestions import suggest_protocol_from_corpus
from app.service.protocol_validation_runs import validate_revision
from app.service.review import create_case

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


async def _project_state(
    session: AsyncSession,
) -> tuple[Project, User, User, ElanFile]:
    instance = Instance(
        instance_name="Protocol Lab",
        institution_name="Protocol Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    admin = User(
        username="protocol-admin",
        email="protocol-admin@example.org",
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
    researcher = User(
        username="protocol-researcher",
        email="protocol-researcher@example.org",
        hashed_password="fixture",  # noqa: S106
        first_name="Rae",
        last_name="Researcher",
        affiliation="Institute",
        department="Linguistics",
        activation_code="fixture",
        is_verified_account=True,
        role=UserRole.PUBLIC,
        instance=instance,
    )
    session.add_all([instance, admin, researcher])
    await session.flush()
    project = Project(
        project_name="Governed Corpus",
        description="Protocol fixture",
        instance_id=instance.instance_id,
        project_path="governed-corpus",
    )
    session.add(project)
    await session.flush()
    session.add(
        UserToProject(
            project_id=project.project_id,
            user_id=researcher.user_id,
            permission=ProjectPermission.READ,
        )
    )
    document = parse_eaf(FIXTURE.read_bytes())
    content = FileContent(
        filename=FIXTURE.name,
        file_size=len(document.raw_xml),
        content_hash=document.sha256,
        user_id=researcher.user_id,
    )
    session.add(content)
    await session.flush()
    elan_file = ElanFile(
        content_id=content.content_id,
        project_id=project.project_id,
        filename=FIXTURE.name,
        file_path=f"governed-corpus/elan_files/{FIXTURE.name}",
        last_modified=content.created_at,
    )
    session.add(elan_file)
    await session.flush()
    return project, admin, researcher, elan_file


@pytest.mark.asyncio
async def test_suggest_protocol_from_latest_real_eaf_revision(
    session: AsyncSession,
) -> None:
    project, _admin, researcher, elan_file = await _project_state(session)
    document = parse_eaf(FIXTURE.read_bytes())
    await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=researcher.user_id,
    )

    suggestion = await suggest_protocol_from_corpus(session, project)

    assert suggestion.total_files == 1
    assert suggestion.analyzed_files == 1
    assert suggestion.skipped_files == []
    assert suggestion.proposed_rules.required_tiers == ["translation", "utterance"]
    assert suggestion.proposed_rules.tier_parents == {"translation": "utterance"}
    assert suggestion.proposed_rules.tier_linguistic_types == {
        "translation": "translation-type",
        "utterance": "utterance-type",
    }
    assert suggestion.proposed_rules.required_controlled_vocabularies == ["greetings"]
    assert suggestion.proposed_rules.media_required is True
    assert suggestion.proposed_rules.allowed_media_mime_types == ["video/mp4"]


@pytest.mark.asyncio
async def test_publish_pin_and_validate_real_eaf_with_delegated_permission(
    session: AsyncSession,
) -> None:
    """Exercise the full protocol lifecycle against an immutable real EAF."""
    project, admin, researcher, elan_file = await _project_state(session)
    grant = await grant_protocol_manager(
        session,
        project=project,
        user_id=researcher.user_id,
        actor_user_id=admin.user_id,
    )
    assert grant.capability == ProjectCapability.MANAGE_PROTOCOLS

    protocol = await create_protocol(
        session,
        project=project,
        name="LSFB baseline",
        description="Required research tiers",
        rules=ProtocolRules(
            required_tiers=["translation", "utterance", "utterance"],
            tier_parents={"translation": "utterance"},
            tier_linguistic_types={
                "utterance": "utterance-type",
                "translation": "translation-type",
            },
            required_controlled_vocabularies=["greetings"],
            media_required=True,
            allowed_media_mime_types=["video/mp4"],
        ),
        actor_user_id=researcher.user_id,
    )
    draft = protocol.versions[0]
    assert draft.rules["required_tiers"] == ["translation", "utterance"]
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=draft.protocol_version_id,
        actor_user_id=researcher.user_id,
    )
    assert published.status == ProtocolVersionStatus.PUBLISHED
    assert published.rules_sha256 is not None and len(published.rules_sha256) == 64
    await pin_protocol_version(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=researcher.user_id,
    )
    document = parse_eaf(FIXTURE.read_bytes())
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=researcher.user_id,
    )

    first_run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )
    repeated_run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )
    await session.commit()

    assert repeated_run.validation_run_id == first_run.validation_run_id
    assert first_run.outcome == ValidationOutcome.PASSED
    assert first_run.issues == []
    assert await session.scalar(select(ProjectCapabilityGrant)) is not None
    assert await session.scalar(select(ValidationRun)) is not None
    project_id = project.project_id
    researcher_id = researcher.user_id
    session.expire_all()
    project_users = await get_project_users(session, project_id)
    researcher_row = next(
        row for row in project_users if row["user_id"] == researcher_id
    )
    assert researcher_row["capabilities"] == ["manage_protocols"]
    actions = set((await session.scalars(select(AuditEvent.action))).all())
    assert {
        "project.capability.granted",
        "protocol.version.published",
        "project.protocol.pinned",
    } <= actions


@pytest.mark.asyncio
async def test_missing_required_tier_is_persisted_as_structured_evidence(
    session: AsyncSession,
) -> None:
    project, admin, _, elan_file = await _project_state(session)
    protocol = await create_protocol(
        session,
        project=project,
        name="Strict tiers",
        description=None,
        rules=ProtocolRules(required_tiers=["nonexistent-tier"]),
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
    document = parse_eaf(FIXTURE.read_bytes())
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )

    run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )
    await session.commit()

    assert run.outcome == ValidationOutcome.FAILED
    assert len(run.issues) == 1
    assert run.issues[0].code == "protocol.required_tier_missing"
    assert run.issues[0].rule_key == "required_tiers"
    with pytest.raises(DBAPIError, match="validation evidence is immutable"):
        await session.execute(
            text(
                'UPDATE "VALIDATION_RUN" SET outcome = :outcome '
                "WHERE validation_run_id = :run_id"
            ),
            {"outcome": "passed", "run_id": run.validation_run_id},
        )


@pytest.mark.asyncio
async def test_published_version_is_immutable_in_service_and_postgresql(
    session: AsyncSession,
) -> None:
    project, admin, _, _ = await _project_state(session)
    protocol = await create_protocol(
        session,
        project=project,
        name="Immutable protocol",
        description=None,
        rules=ProtocolRules(),
        actor_user_id=admin.user_id,
    )
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=protocol.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    await session.commit()

    with pytest.raises(ProtocolConflictError, match="immutable"):
        await update_draft(
            session,
            project=project,
            protocol_version_id=published.protocol_version_id,
            rules=ProtocolRules(required_tiers=["changed"]),
        )


@pytest.mark.asyncio
async def test_drafts_delete_but_published_versions_archive(
    session: AsyncSession,
) -> None:
    project, admin, _, _ = await _project_state(session)
    disposable = await create_protocol(
        session,
        project=project,
        name="Mistaken draft",
        description=None,
        rules=ProtocolRules(required_tiers=["typo"]),
        actor_user_id=admin.user_id,
    )
    await delete_protocol_draft(
        session,
        project=project,
        protocol_version_id=disposable.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    retained = await create_protocol(
        session,
        project=project,
        name="Published mistake",
        description=None,
        rules=ProtocolRules(required_tiers=["wrong-tier"]),
        actor_user_id=admin.user_id,
    )
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=retained.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    archived = await archive_protocol_version(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=admin.user_id,
        reason="Incorrect tier name",
    )
    await session.commit()

    assert archived.archived_at is not None
    assert archived.archive_reason == "Incorrect tier name"
    with pytest.raises(ProtocolConflictError, match="archived"):
        await pin_protocol_version(
            session,
            project=project,
            protocol_version_id=archived.protocol_version_id,
            actor_user_id=admin.user_id,
        )
    with pytest.raises(DBAPIError, match="published protocol versions are immutable"):
        await session.execute(
            text(
                'UPDATE "PROTOCOL_VERSION" SET rules = :rules '
                "WHERE protocol_version_id = :version_id"
            ),
            {
                "rules": '{"required_tiers": ["bypassed"]}',
                "version_id": published.protocol_version_id,
            },
        )


@pytest.mark.asyncio
async def test_upload_boundary_blocks_and_preserves_protocol_violations(
    session: AsyncSession,
) -> None:
    project, admin, researcher, _ = await _project_state(session)
    protocol = await create_protocol(
        session,
        project=project,
        name="Upload gate",
        description="Required before collaborative review",
        rules=ProtocolRules(required_tiers=["tier-required-by-project"]),
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
    await session.commit()
    upload = UploadFile(
        file=BytesIO(FIXTURE.read_bytes()),
        filename="protocol-check.eaf",
        size=FIXTURE.stat().st_size,
    )

    with pytest.raises(ElanoraError) as rejected:
        await validate_and_record_elan_files(
            [upload],
            db=session,
            instance_id=project.instance_id,
            project_id=project.project_id,
            requested_project_name=project.project_name,
            submitted_by=researcher.user_id,
        )

    assert rejected.value.status_code == 422
    assert rejected.value.code == "invalid_eaf_batch"
    assert (
        rejected.value.params["rejected_files"][0]["issues"][0]["code"]
        == "protocol.required_tier_missing"
    )
    attempt = await session.scalar(
        select(EafIngestionAttempt).where(
            EafIngestionAttempt.project_id == project.project_id
        )
    )
    assert attempt is not None
    assert attempt.raw_xml == FIXTURE.read_bytes()
    assert attempt.validation_issues[0]["code"] == "protocol.required_tier_missing"


@pytest.mark.asyncio
async def test_project_scan_previews_latest_revisions_and_opens_correction(
    session: AsyncSession,
) -> None:
    """A retroactive scan is durable and its finding can enter the review flow."""
    project, admin, _, elan_file = await _project_state(session)
    protocol = await create_protocol(
        session,
        project=project,
        name="Future corpus standard",
        description=None,
        rules=ProtocolRules(required_tiers=["future-required-tier"]),
        actor_user_id=admin.user_id,
    )
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=protocol.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    document = parse_eaf(FIXTURE.read_bytes())
    await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )

    created = await run_compliance_scan(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=admin.user_id,
        trigger="preview",
    )
    await session.commit()
    loaded = (await list_compliance_scans(session, project=project))[0]
    response = compliance_scan_response(loaded)
    issue = response.files[0].issues[0]
    correction = await create_case(
        session,
        project_id=project.project_id,
        actor_id=admin.user_id,
        request=ReviewCaseCreate(
            validation_issue_id=issue.validation_issue_id,
            filename=response.files[0].filename,
            title="Add the required tier",
            initial_comment=issue.message,
        ),
    )

    assert created.scan_id == response.scan_id
    assert response.trigger == "preview"
    assert response.total_files == 1
    assert response.failed_files == 1
    assert response.files[0].outcome == ValidationOutcome.FAILED
    assert correction.upload_id is None
    assert correction.validation_issue_id == issue.validation_issue_id
    assert await session.scalar(select(ProjectComplianceScan)) is not None


@pytest.mark.asyncio
async def test_unused_archived_version_and_preview_can_be_purged(
    session: AsyncSession,
) -> None:
    project, admin, _, elan_file = await _project_state(session)
    protocol = await create_protocol(
        session,
        project=project,
        name="Accidental publication",
        description=None,
        rules=ProtocolRules(required_tiers=["mistyped-tier"]),
        actor_user_id=admin.user_id,
    )
    published = await publish_protocol_version(
        session,
        project=project,
        protocol_version_id=protocol.versions[0].protocol_version_id,
        actor_user_id=admin.user_id,
    )
    document = parse_eaf(FIXTURE.read_bytes())
    await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )
    await run_compliance_scan(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=admin.user_id,
        trigger="preview",
    )
    await archive_protocol_version(
        session,
        project=project,
        protocol_version_id=published.protocol_version_id,
        actor_user_id=admin.user_id,
        reason="Mistyped rule",
    )
    version_id = published.protocol_version_id
    await purge_archived_protocol_version(
        session,
        project=project,
        protocol_version_id=version_id,
        actor_user_id=admin.user_id,
    )
    await session.commit()

    assert await session.get(ProtocolVersion, version_id) is None
    assert await session.scalar(select(ProjectComplianceScan)) is None
    tombstone = await session.scalar(
        select(AuditEvent).where(AuditEvent.action == "protocol.version.purged")
    )
    assert tombstone is not None
    assert tombstone.details["rules_sha256"] is not None


async def _pinned(
    session: AsyncSession, project: Project, admin: User, rules: ProtocolRules
) -> ProtocolVersion:
    protocol = await create_protocol(
        session,
        project=project,
        name="Severity protocol",
        description=None,
        rules=rules,
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
    return published


WARN_ON_MISSING_TIER = ProtocolRules(
    required_tiers=["tier-still-being-annotated"],
    severities={"required_tiers": ValidationSeverity.WARNING},
)


@pytest.mark.asyncio
async def test_a_warning_rule_lets_the_upload_through_and_records_the_warning(
    session: AsyncSession,
) -> None:
    project, admin, researcher, _ = await _project_state(session)
    await _pinned(session, project, admin, WARN_ON_MISSING_TIER)
    await session.commit()
    upload = UploadFile(
        file=BytesIO(FIXTURE.read_bytes()),
        filename="in-progress.eaf",
        size=FIXTURE.stat().st_size,
    )

    batch = await validate_and_record_elan_files(
        [upload],
        db=session,
        instance_id=project.instance_id,
        project_id=project.project_id,
        requested_project_name=project.project_name,
        submitted_by=researcher.user_id,
    )

    assert batch.files == [upload]
    assert batch.protocol_outcome == "passed"
    assert [warning["code"] for warning in batch.protocol_warnings] == [
        "protocol.required_tier_missing"
    ]
    assert batch.protocol_warnings[0]["filename"] == "in-progress.eaf"
    rejected = await session.scalar(
        select(EafIngestionAttempt).where(
            EafIngestionAttempt.project_id == project.project_id
        )
    )
    assert rejected is None


@pytest.mark.asyncio
async def test_a_run_with_only_warnings_passes_and_keeps_them_as_evidence(
    session: AsyncSession,
) -> None:
    project, admin, _, elan_file = await _project_state(session)
    await _pinned(session, project, admin, WARN_ON_MISSING_TIER)
    document = parse_eaf(FIXTURE.read_bytes())
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )

    run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )

    assert run.outcome == ValidationOutcome.PASSED
    (issue,) = run.issues
    assert issue.severity == ValidationSeverity.WARNING
    assert issue.rule_key == "required_tiers"


@pytest.mark.asyncio
async def test_new_rule_families_survive_publication_and_fail_a_run(
    session: AsyncSession,
) -> None:
    """Rules round-trip through the stored snapshot, not only the in-memory model."""
    project, admin, _, elan_file = await _project_state(session)
    rules = ProtocolRules(
        required_tiers=["translation", "utterance"],
        vocabulary_tiers=["translation"],
        annotator_tiers=["utterance"],
        linguistic_type_constraints={"translation-type": "Symbolic_Subdivision"},
        severities={"annotator_tiers": ValidationSeverity.WARNING},
    )
    published = await _pinned(session, project, admin, rules)
    assert ProtocolRules.model_validate(published.rules) == rules
    content = FIXTURE.read_bytes().replace(b' ANNOTATOR="A01"', b"", 1)
    document = parse_eaf(content)
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )

    run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )

    assert run.outcome == ValidationOutcome.FAILED
    assert [(issue.rule_key, issue.severity) for issue in run.issues] == [
        ("vocabulary_tiers", ValidationSeverity.ERROR),
        ("annotator_tiers", ValidationSeverity.WARNING),
        ("linguistic_type_constraints", ValidationSeverity.ERROR),
    ]


SESSION_NAMES = ProtocolRules(
    filename_standard={
        "name": "Session files",
        "pattern": "session-{number}",
        "components": [{"name": "number", "regex": "[0-9]{3}"}],
    }
)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("filename", "accepted"), [("session-001.eaf", True), ("notes.eaf", False)]
)
async def test_a_pinned_filename_standard_judges_uploads(
    session: AsyncSession, filename: str, accepted: bool
) -> None:
    project, admin, researcher, _ = await _project_state(session)
    await _pinned(session, project, admin, SESSION_NAMES)
    await session.commit()
    upload = UploadFile(
        file=BytesIO(FIXTURE.read_bytes()),
        filename=filename,
        size=FIXTURE.stat().st_size,
    )
    arguments = {
        "db": session,
        "instance_id": project.instance_id,
        "project_id": project.project_id,
        "requested_project_name": project.project_name,
        "submitted_by": researcher.user_id,
    }

    if accepted:
        batch = await validate_and_record_elan_files([upload], **arguments)
        assert batch.files == [upload]
        return
    with pytest.raises(ElanoraError) as rejected:
        await validate_and_record_elan_files([upload], **arguments)
    (issue,) = rejected.value.params["rejected_files"][0]["issues"]
    assert issue["code"] == "protocol.filename_not_compliant"


@pytest.mark.asyncio
async def test_a_validation_run_judges_the_stored_filename(
    session: AsyncSession,
) -> None:
    project, admin, _, elan_file = await _project_state(session)
    await _pinned(session, project, admin, SESSION_NAMES)
    document = parse_eaf(FIXTURE.read_bytes())
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=admin.user_id,
    )

    run = await validate_revision(
        session, project=project, revision_id=revision.revision_id
    )

    assert run.outcome == ValidationOutcome.FAILED
    (issue,) = run.issues
    assert issue.code == "protocol.filename_not_compliant"
    assert FIXTURE.name in issue.message
