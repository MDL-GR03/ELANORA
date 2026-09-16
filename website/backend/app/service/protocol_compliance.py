"""Scanning a project's accepted corpus against a protocol version."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import (
    ProtocolVersionStatus,
    ValidationOutcome,
)
from app.model.project import Project
from app.model.protocol import (
    ProjectComplianceScan,
    ProjectComplianceScanFile,
    ProtocolVersion,
    ValidationRun,
)
from app.schema.protocol import (
    ComplianceScanFileResponse,
    ComplianceScanResponse,
    ValidationIssueResponse,
)
from app.service.protocol_errors import (
    ProtocolConflictError,
)
from app.service.protocol_shared import _scoped_version
from app.service.protocol_validation_runs import validate_revision_against_version

FULL_COVERAGE_PERCENT = 100.0


async def run_compliance_scan(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
    trigger: str,
) -> ProjectComplianceScan:
    """Validate every latest accepted EAF revision and persist the snapshot."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("Compliance scans require a published protocol")
    if version.archive is not None:
        raise ProtocolConflictError("Archived protocol versions cannot start new scans")
    if trigger not in {"manual", "preview", "protocol_pinned"}:
        raise ProtocolConflictError("Unsupported compliance scan trigger")

    latest_number = (
        select(
            EafRevision.elan_id,
            func.max(EafRevision.revision_number).label("revision_number"),
        )
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project.project_id)
        .group_by(EafRevision.elan_id)
        .subquery()
    )
    revisions = list(
        (
            await db.scalars(
                select(EafRevision)
                .join(
                    latest_number,
                    (latest_number.c.elan_id == EafRevision.elan_id)
                    & (latest_number.c.revision_number == EafRevision.revision_number),
                )
                .options(selectinload(EafRevision.elan_file))
                .order_by(EafRevision.elan_id)
            )
        ).all()
    )
    scan = ProjectComplianceScan(
        project_id=project.project_id,
        protocol_version_id=protocol_version_id,
        status="running",
        trigger=trigger,
        initiated_by=actor_user_id,
        total_files=len(revisions),
        files=[],
    )
    db.add(scan)
    await db.flush()
    for revision in revisions:
        run = await validate_revision_against_version(
            db,
            project=project,
            revision_id=revision.revision_id,
            protocol_version_id=protocol_version_id,
        )
        scan.files.append(
            ProjectComplianceScanFile(
                elan_id=revision.elan_id,
                revision_id=revision.revision_id,
                validation_run_id=run.validation_run_id,
                outcome=run.outcome,
            )
        )
        if run.outcome == ValidationOutcome.PASSED:
            scan.passed_files += 1
        else:
            scan.failed_files += 1
    scan.status = "completed"
    scan.completed_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="project.compliance.scanned",
            resource_type="compliance_scan",
            resource_id=str(scan.scan_id),
            details={
                "trigger": trigger,
                "protocol_version_id": str(protocol_version_id),
                "total_files": scan.total_files,
                "failed_files": scan.failed_files,
            },
        )
    )
    await db.flush()
    return scan


async def list_compliance_scans(
    db: AsyncSession, *, project: Project, limit: int = 10
) -> list[ProjectComplianceScan]:
    """Return recent scans with all researcher-facing evidence loaded."""
    return list(
        (
            await db.scalars(
                select(ProjectComplianceScan)
                .where(ProjectComplianceScan.project_id == project.project_id)
                .options(
                    selectinload(ProjectComplianceScan.protocol_version).selectinload(
                        ProtocolVersion.protocol
                    ),
                    selectinload(ProjectComplianceScan.files).selectinload(
                        ProjectComplianceScanFile.elan_file
                    ),
                    selectinload(ProjectComplianceScan.files)
                    .selectinload(ProjectComplianceScanFile.validation_run)
                    .selectinload(ValidationRun.issues),
                )
                .order_by(ProjectComplianceScan.started_at.desc())
                .limit(limit)
            )
        )
        .unique()
        .all()
    )


def compliance_scan_response(scan: ProjectComplianceScan) -> ComplianceScanResponse:
    """Translate loaded persistence records into a stable API representation."""
    version = scan.protocol_version
    return ComplianceScanResponse(
        scan_id=scan.scan_id,
        project_id=scan.project_id,
        protocol_version_id=scan.protocol_version_id,
        protocol_name=version.protocol.name,
        protocol_version_number=version.version_number,
        status=scan.status,
        trigger=scan.trigger,
        total_files=scan.total_files,
        passed_files=scan.passed_files,
        failed_files=scan.failed_files,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        error_summary=scan.error_summary,
        files=[
            ComplianceScanFileResponse(
                scan_file_id=item.scan_file_id,
                elan_id=item.elan_id,
                revision_id=item.revision_id,
                filename=item.elan_file.filename,
                outcome=ValidationOutcome(item.outcome),
                validation_run_id=item.validation_run_id,
                issues=[
                    ValidationIssueResponse.model_validate(issue)
                    for issue in item.validation_run.issues
                ],
            )
            for item in sorted(scan.files, key=lambda value: value.elan_file.filename)
        ],
    )
