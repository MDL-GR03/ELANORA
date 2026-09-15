"""Destroying a deleted project's content once its retention period ends.

A project is purged only when it has been deleted, carries a retention period,
that period has passed, and no legal hold is in place. The project row stays as
a tombstone so its name remains reserved and the audit trail keeps its meaning.

What goes: ELAN files with their annotations and revisions, project revision
manifests, contributions and their reviews, rejected upload attempts, compliance
scans, validation evidence for the destroyed revisions, and the project's Git
export and recovery copy. What stays: the project row, its governance, its
members, and the audit events, including one recording the purge itself.
"""

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.model.annotation import Annotation
from app.model.association import ElanFileToTier
from app.model.audit_event import AuditEvent
from app.model.contribution_change_set import ContributionChangeSet
from app.model.eaf_ingestion_attempt import EafIngestionAttempt
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.model.project_revision import ProjectRevision, ProjectRevisionEaf
from app.model.protocol import (
    ProjectComplianceScan,
    ProtocolValidationIssue,
    ValidationRun,
)
from app.model.review import ReviewCase
from app.model.tier_group import TierGroup
from app.model.tier_section import TierSection
from app.storage.paths import safe_project_path
from app.utils.file_processing import get_elanora_projects_base_path
from app.utils.project_backup import create_hidden_folder_in_root

logger = get_logger()


@dataclass
class PurgeReport:
    """Which projects were purged, and what each one contained."""

    purged: list[dict[str, Any]] = field(default_factory=list)


async def purgeable_projects(
    db: AsyncSession, *, now: datetime | None = None
) -> list[Project]:
    """Deleted projects whose retention period has ended, without a legal hold."""
    moment = now or datetime.now(UTC)
    candidates = (
        await db.scalars(
            select(Project)
            .where(
                Project.deleted_at.is_not(None),
                Project.retention_days.is_not(None),
                Project.legal_hold.is_(False),
                Project.content_purged_at.is_(None),
            )
            .order_by(Project.project_id)
        )
    ).all()
    return [
        project
        for project in candidates
        if project.deleted_at is not None
        and project.retention_days is not None
        and project.deleted_at + timedelta(days=project.retention_days) <= moment
    ]


async def purge_expired_projects(
    db: AsyncSession, *, dry_run: bool = False, now: datetime | None = None
) -> PurgeReport:
    """Purge every project that is due, reporting what each one held.

    The caller commits. A dry run reports the same content counts and destroys
    nothing, in the database or on disk.
    """
    report = PurgeReport()
    for project in await purgeable_projects(db, now=now):
        counts = await _content_counts(db, project.project_id)
        report.purged.append(
            {
                "project_id": project.project_id,
                "project_name": project.project_name,
                "deleted_at": project.deleted_at.isoformat()
                if project.deleted_at
                else None,
                "retention_days": project.retention_days,
                **counts,
            }
        )
        if dry_run:
            continue
        await _purge_project(db, project, counts)
    return report


async def _content_counts(db: AsyncSession, project_id: int) -> dict[str, int]:
    files = select(ElanFile.elan_id).where(ElanFile.project_id == project_id)
    statements = {
        "files": select(func.count())
        .select_from(ElanFile)
        .where(ElanFile.project_id == project_id),
        "revisions": select(func.count())
        .select_from(EafRevision)
        .where(EafRevision.elan_id.in_(files)),
        "annotations": select(func.count())
        .select_from(Annotation)
        .where(Annotation.elan_id.in_(files)),
        "manifests": select(func.count())
        .select_from(ProjectRevision)
        .where(ProjectRevision.project_id == project_id),
        "contributions": select(func.count())
        .select_from(PendingUpload)
        .where(PendingUpload.project_id == project_id),
        "rejected_uploads": select(func.count())
        .select_from(EafIngestionAttempt)
        .where(EafIngestionAttempt.project_id == project_id),
    }
    return {
        name: int(await db.scalar(statement) or 0)
        for name, statement in statements.items()
    }


async def _purge_project(
    db: AsyncSession, project: Project, counts: dict[str, int]
) -> None:
    project_id = project.project_id
    project_name = project.project_name
    files = select(ElanFile.elan_id).where(ElanFile.project_id == project_id)
    revisions = select(EafRevision.revision_id).where(EafRevision.elan_id.in_(files))
    manifests = select(ProjectRevision.revision_id).where(
        ProjectRevision.project_id == project_id
    )
    runs = select(ValidationRun.validation_run_id).where(
        ValidationRun.revision_id.in_(revisions)
    )

    # The ledger and validation evidence refuse deletion outside a purge.
    await db.execute(text("SET LOCAL elanora.allow_retention_purge = 'on'"))
    project.current_revision_id = None
    await db.flush()

    await db.execute(
        delete(ProjectComplianceScan).where(
            ProjectComplianceScan.project_id == project_id
        )
    )
    await db.execute(
        delete(ProtocolValidationIssue).where(
            ProtocolValidationIssue.validation_run_id.in_(runs)
        )
    )
    await db.execute(
        delete(ValidationRun).where(ValidationRun.revision_id.in_(revisions))
    )
    await db.execute(
        delete(ProjectIntegrityStatus).where(
            ProjectIntegrityStatus.project_id == project_id
        )
    )
    await db.execute(delete(ReviewCase).where(ReviewCase.project_id == project_id))
    await db.execute(
        delete(ContributionChangeSet).where(
            ContributionChangeSet.project_id == project_id
        )
    )
    await db.execute(
        delete(ProjectRevisionEaf).where(
            ProjectRevisionEaf.project_revision_id.in_(manifests)
        )
    )
    await db.execute(
        delete(ProjectRevision).where(ProjectRevision.project_id == project_id)
    )
    # Contributions point at the ones they supersede.
    await db.execute(
        update(PendingUpload)
        .where(PendingUpload.project_id == project_id)
        .values(superseded_by_upload_id=None)
    )
    await db.execute(
        delete(PendingUpload).where(PendingUpload.project_id == project_id)
    )
    content_ids = set(
        (
            await db.scalars(
                select(ElanFile.content_id).where(ElanFile.project_id == project_id)
            )
        ).all()
    )
    # Tables that hold research structure without a cascade of their own.
    await db.execute(delete(ElanFileToTier).where(ElanFileToTier.elan_id.in_(files)))
    await db.execute(delete(TierGroup).where(TierGroup.project_id == project_id))
    await db.execute(delete(TierSection).where(TierSection.project_id == project_id))
    await db.execute(delete(ElanFile).where(ElanFile.project_id == project_id))
    await db.execute(
        delete(EafIngestionAttempt).where(EafIngestionAttempt.project_id == project_id)
    )
    if content_ids:
        # File content is shared by identical bytes; keep what another project uses.
        still_used = set(
            (
                await db.scalars(
                    select(ElanFile.content_id).where(
                        ElanFile.content_id.in_(content_ids)
                    )
                )
            ).all()
        )
        orphaned = content_ids - still_used
        if orphaned:
            await db.execute(
                delete(FileContent).where(FileContent.content_id.in_(orphaned))
            )

    project.content_purged_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=None,
            project_id=project_id,
            action="project.content.purged",
            resource_type="project",
            resource_id=str(project_id),
            details={"retention_days": project.retention_days, **counts},
        )
    )
    await db.flush()
    _remove_stored_files(project_name)
    logger.info("Purged the content of a project whose retention period ended")


def _remove_stored_files(project_name: str) -> None:
    """Remove the Git export and the same-host recovery copy."""
    roots = [Path(get_elanora_projects_base_path()), create_hidden_folder_in_root()]
    for root in roots:
        try:
            shutil.rmtree(safe_project_path(root, project_name), ignore_errors=True)
        except ValueError:
            logger.warning("Refused an unsafe project path while purging content")
