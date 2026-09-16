"""Drafting, publishing, pinning, archiving and purging protocol versions."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.audit_event import AuditEvent
from app.model.enums import (
    ProtocolVersionStatus,
)
from app.model.project import Project
from app.model.protocol import (
    ProjectComplianceScan,
    ProjectComplianceScanFile,
    Protocol,
    ProtocolValidationIssue,
    ProtocolVersion,
    ProtocolVersionArchive,
    ValidationRun,
)
from app.model.review import ReviewCase
from app.schema.protocol import (
    ProtocolRules,
)
from app.service.protocol_errors import (
    ProtocolConflictError,
    ProtocolNotFoundError,
)
from app.service.protocol_shared import _rules_checksum, _rules_dict, _scoped_version


async def create_protocol(
    db: AsyncSession,
    *,
    project: Project,
    name: str,
    description: str | None,
    rules: ProtocolRules,
    actor_user_id: int | None,
) -> Protocol:
    """Create an institution protocol and its first mutable draft."""
    protocol = Protocol(
        instance_id=project.instance_id,
        name=name.strip(),
        description=description,
        created_by=actor_user_id,
    )
    protocol.versions.append(
        ProtocolVersion(
            version_number=1,
            status=ProtocolVersionStatus.DRAFT,
            rules=_rules_dict(rules),
            created_by=actor_user_id,
        )
    )
    db.add(protocol)
    await db.flush()
    # Responses read each version's archive; loading it now keeps serialization
    # from lazy-loading outside the async context.
    await db.refresh(protocol.versions[0], attribute_names=["archive"])
    return protocol


async def list_protocols(db: AsyncSession, project: Project) -> list[Protocol]:
    """List only protocols owned by the project's institution."""
    return list(
        (
            await db.scalars(
                select(Protocol)
                .where(Protocol.instance_id == project.instance_id)
                .options(
                    selectinload(Protocol.versions).selectinload(
                        ProtocolVersion.archive
                    )
                )
                .order_by(Protocol.name)
            )
        ).all()
    )


async def create_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_id: uuid.UUID,
    rules: ProtocolRules,
    actor_user_id: int | None,
) -> ProtocolVersion:
    """Append the next draft version while serializing version allocation."""
    protocol = await db.scalar(
        select(Protocol)
        .where(
            Protocol.protocol_id == protocol_id,
            Protocol.instance_id == project.instance_id,
        )
        .with_for_update()
    )
    if protocol is None:
        raise ProtocolNotFoundError("Protocol not found")
    next_version = await db.scalar(
        select(func.coalesce(func.max(ProtocolVersion.version_number), 0) + 1).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    version = ProtocolVersion(
        protocol_id=protocol_id,
        version_number=next_version,
        status=ProtocolVersionStatus.DRAFT,
        rules=_rules_dict(rules),
        created_by=actor_user_id,
    )
    db.add(version)
    await db.flush()
    await db.refresh(version, attribute_names=["archive"])
    return version


async def update_draft(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    rules: ProtocolRules,
) -> ProtocolVersion:
    """Replace rules only while the selected version remains a draft."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Published protocol versions are immutable")
    version.rules = _rules_dict(rules)
    await db.flush()
    return version


async def publish_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> ProtocolVersion:
    """Freeze a draft and append auditable publication evidence."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Protocol version is already published")
    validated_rules = ProtocolRules.model_validate(version.rules)
    version.rules = _rules_dict(validated_rules)
    version.rules_sha256 = _rules_checksum(version.rules)
    version.status = ProtocolVersionStatus.PUBLISHED
    version.published_by = actor_user_id
    version.published_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.published",
            resource_type="protocol_version",
            resource_id=str(version.protocol_version_id),
            details={"rules_sha256": version.rules_sha256},
        )
    )
    await db.flush()
    return version


async def pin_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> ProtocolVersion:
    """Pin a project to a published protocol owned by its institution."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("A project can only pin a published protocol")
    if version.archive is not None:
        raise ProtocolConflictError("An archived protocol version cannot be activated")
    project.protocol_version_id = version.protocol_version_id
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="project.protocol.pinned",
            resource_type="protocol_version",
            resource_id=str(version.protocol_version_id),
            details={},
        )
    )
    await db.flush()
    return version


async def delete_protocol_draft(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> None:
    """Delete a draft; published research evidence is never deletable."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Published protocol versions cannot be deleted")
    protocol_id = version.protocol_id
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.draft.deleted",
            resource_type="protocol_version",
            resource_id=str(protocol_version_id),
            details={"protocol_id": str(protocol_id)},
        )
    )
    version_count = await db.scalar(
        select(func.count(ProtocolVersion.protocol_version_id)).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    if version_count == 1:
        protocol = await db.get(Protocol, protocol_id)
        if protocol is not None:
            await db.delete(protocol)
    else:
        await db.delete(version)
    await db.flush()


async def archive_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
    reason: str | None,
) -> ProtocolVersion:
    """Withdraw a published version from future use without mutating it."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("Draft versions should be deleted, not archived")
    if version.archive is not None:
        raise ProtocolConflictError("Protocol version is already archived")
    active_project = await db.scalar(
        select(Project.project_id).where(
            Project.protocol_version_id == protocol_version_id,
            Project.deleted_at.is_(None),
        )
    )
    if active_project is not None:
        raise ProtocolConflictError(
            "Replace the active project protocol before archiving this version"
        )
    archive = ProtocolVersionArchive(
        protocol_version_id=protocol_version_id,
        archived_by=actor_user_id,
        reason=reason.strip() if reason else None,
    )
    db.add(archive)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.archived",
            resource_type="protocol_version",
            resource_id=str(protocol_version_id),
            details={"reason": archive.reason},
        )
    )
    await db.flush()
    version.archive = archive
    return version


async def purge_archived_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> None:
    """Purge an unused mistake plus disposable previews, retaining a tombstone."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.PUBLISHED or version.archive is None:
        raise ProtocolConflictError("Only archived published versions can be purged")
    version_id_text = str(protocol_version_id)
    was_activated = await db.scalar(
        select(AuditEvent.event_id).where(
            AuditEvent.action == "project.protocol.pinned",
            AuditEvent.resource_type == "protocol_version",
            AuditEvent.resource_id == version_id_text,
        )
    )
    if was_activated is not None:
        raise ProtocolConflictError(
            "This version was activated and must remain in the research history"
        )
    if (
        await db.scalar(
            select(Project.project_id).where(
                Project.protocol_version_id == protocol_version_id
            )
        )
        is not None
    ):
        raise ProtocolConflictError("The active project protocol cannot be purged")
    non_preview_scan = await db.scalar(
        select(ProjectComplianceScan.scan_id).where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger != "preview",
        )
    )
    if non_preview_scan is not None:
        raise ProtocolConflictError(
            "This version has a non-preview compliance scan and must be retained"
        )
    preview_run_ids = (
        select(ProjectComplianceScanFile.validation_run_id)
        .join(
            ProjectComplianceScan,
            ProjectComplianceScan.scan_id == ProjectComplianceScanFile.scan_id,
        )
        .where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger == "preview",
        )
    )
    external_run = await db.scalar(
        select(ValidationRun.validation_run_id).where(
            ValidationRun.protocol_version_id == protocol_version_id,
            ValidationRun.validation_run_id.not_in(preview_run_ids),
        )
    )
    if external_run is not None:
        raise ProtocolConflictError(
            "This version validated work outside a preview and must be retained"
        )
    reviewed_issue = await db.scalar(
        select(ReviewCase.case_id)
        .join(
            ProtocolValidationIssue,
            ProtocolValidationIssue.validation_issue_id
            == ReviewCase.validation_issue_id,
        )
        .join(
            ValidationRun,
            ValidationRun.validation_run_id
            == ProtocolValidationIssue.validation_run_id,
        )
        .where(ValidationRun.protocol_version_id == protocol_version_id)
    )
    if reviewed_issue is not None:
        raise ProtocolConflictError(
            "A correction discussion references this version, so it must be retained"
        )

    protocol_id = version.protocol_id
    version_count = await db.scalar(
        select(func.count(ProtocolVersion.protocol_version_id)).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    rules_checksum = version.rules_sha256
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.purged",
            resource_type="protocol_version_tombstone",
            resource_id=version_id_text,
            details={
                "protocol_id": str(protocol_id),
                "version_number": version.version_number,
                "rules_sha256": rules_checksum,
                "archive_reason": version.archive.reason,
            },
        )
    )
    await db.flush()
    await db.execute(
        delete(ProjectComplianceScan).where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger == "preview",
        )
    )
    run_ids = select(ValidationRun.validation_run_id).where(
        ValidationRun.protocol_version_id == protocol_version_id
    )
    await db.execute(text("SET LOCAL elanora.allow_protocol_purge = 'on'"))
    await db.execute(
        delete(ProtocolValidationIssue).where(
            ProtocolValidationIssue.validation_run_id.in_(run_ids)
        )
    )
    await db.execute(
        delete(ValidationRun).where(
            ValidationRun.protocol_version_id == protocol_version_id
        )
    )
    if version_count == 1:
        protocol = await db.get(Protocol, protocol_id)
        if protocol is not None:
            await db.delete(protocol)
    else:
        await db.delete(version)
    await db.flush()
