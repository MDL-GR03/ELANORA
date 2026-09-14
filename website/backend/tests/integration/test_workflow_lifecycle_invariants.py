"""PostgreSQL guarantees for durable workflow lifecycle records."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.contribution_change_set import ContributionChangeSet
from app.model.enums import ProtocolVersionStatus, Severity, Status, Type
from app.model.instance import Instance
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.project_sync_operation import ProjectSyncOperation
from app.model.protocol import ProjectComplianceScan, Protocol, ProtocolVersion
from app.model.review import ReviewCase


async def _workflow_fixture(
    session: AsyncSession,
) -> tuple[Project, PendingUpload, ProtocolVersion]:
    instance = Instance(
        instance_name="Lifecycle constraints",
        institution_name="Research institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    project = Project(
        project_name="Lifecycle corpus",
        project_path="lifecycle-corpus",
        instance=instance,
    )
    protocol = Protocol(instance=instance, name="Lifecycle protocol")
    protocol_version = ProtocolVersion(
        protocol=protocol,
        version_number=1,
        status=ProtocolVersionStatus.DRAFT,
        rules={},
    )
    session.add_all([instance, project, protocol, protocol_version])
    await session.flush()
    upload = PendingUpload(
        upload_type=Type.UPLOAD_WITH_MODIFICATIONS,
        upload_description="Lifecycle contribution",
        severity=Severity.LOW,
        status=Status.READY_TO_MERGE,
        project_id=project.project_id,
    )
    session.add(upload)
    await session.flush()
    return project, upload, protocol_version


@pytest.mark.asyncio
async def test_terminal_upload_requires_resolution_time(session: AsyncSession) -> None:
    project, _, _ = await _workflow_fixture(session)
    session.add(
        PendingUpload(
            upload_type=Type.PENDING_UPLOAD,
            upload_description="Contradictory upload",
            severity=Severity.LOW,
            status=Status.RESOLVED,
            project_id=project.project_id,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_completed_change_set_requires_time_and_commit(
    session: AsyncSession,
) -> None:
    project, upload, _ = await _workflow_fixture(session)
    session.add(
        ContributionChangeSet(
            project_id=project.project_id,
            upload_id=upload.upload_id,
            branch_name="contribution/lifecycle",
            resolution_strategy="auto",
            expected_commit="a" * 40,
            state="completed",
            attempts=1,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_sync_completion_requires_time_and_result(
    session: AsyncSession,
) -> None:
    project, _, _ = await _workflow_fixture(session)
    session.add(
        ProjectSyncOperation(
            project_id=project.project_id,
            state="completed",
            changes=[],
            evidence_manifest=[],
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_resolved_review_requires_resolution_time(
    session: AsyncSession,
) -> None:
    project, upload, _ = await _workflow_fixture(session)
    session.add(
        ReviewCase(
            project_id=project.project_id,
            upload_id=upload.upload_id,
            title="Contradictory review",
            state="resolved",
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_compliance_counts_cannot_exceed_total(session: AsyncSession) -> None:
    project, _, protocol_version = await _workflow_fixture(session)
    session.add(
        ProjectComplianceScan(
            project_id=project.project_id,
            protocol_version_id=protocol_version.protocol_version_id,
            status="running",
            trigger="manual",
            total_files=1,
            passed_files=1,
            failed_files=1,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_consistent_terminal_workflow_records_remain_valid(
    session: AsyncSession,
) -> None:
    project, upload, protocol_version = await _workflow_fixture(session)
    now = datetime.now(UTC)
    upload.status = Status.RESOLVED
    upload.resolved_at = now.replace(tzinfo=None)
    session.add_all(
        [
            ContributionChangeSet(
                project_id=project.project_id,
                upload_id=upload.upload_id,
                branch_name="contribution/lifecycle",
                resolution_strategy="auto",
                expected_commit="b" * 40,
                resulting_commit="c" * 40,
                state="completed",
                attempts=1,
                completed_at=now,
            ),
            ProjectSyncOperation(
                project_id=project.project_id,
                state="completed",
                changes=[],
                evidence_manifest=[],
                resulting_commit="d" * 40,
                completed_at=now,
            ),
            ReviewCase(
                project_id=project.project_id,
                upload_id=upload.upload_id,
                title="Completed review",
                state="resolved",
                resolved_at=now,
            ),
            ProjectComplianceScan(
                project_id=project.project_id,
                protocol_version_id=protocol_version.protocol_version_id,
                status="completed",
                trigger="manual",
                total_files=2,
                passed_files=1,
                failed_files=1,
                completed_at=now,
            ),
        ]
    )

    await session.flush()
