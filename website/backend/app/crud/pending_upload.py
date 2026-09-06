from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.sql import func

from app.core.centralized_logging import get_logger
from app.model.enums import Severity, Status, Type
from app.model.pending_upload import PendingUpload

logger = get_logger()


async def save_pending_upload(
    db: AsyncSession,
    project_id: int,
    branch_name: str,
    upload_data: dict[str, Any],
    *,
    submitted_by: int,
    base_commit: str,
) -> PendingUpload:
    """Save pending upload info - no conflicts stored."""
    # Create pending upload record
    pending_upload = PendingUpload(
        branch_name=branch_name,
        upload_type=Type.PENDING_UPLOAD,  # New enum value
        upload_description=build_pending_description(upload_data),
        severity=Severity.LOW,  # Informational only
        status=Status.PENDING_ADMIN_APPROVAL,  # New enum value
        detected_at=func.now(),
        git_details=upload_data,
        project_id=project_id,
        submitted_by=submitted_by,
        base_commit=base_commit,
    )
    db.add(pending_upload)
    await db.commit()
    await db.refresh(pending_upload)
    logger.info(f"Saved pending upload for branch: {branch_name}")
    return pending_upload


async def get_pending_uploads(db: AsyncSession, project_id: int) -> list[PendingUpload]:
    """Get pending uploads in a stable, newest-first review order."""
    result = await db.scalars(
        select(PendingUpload)
        .where(
            PendingUpload.project_id == project_id,
            PendingUpload.status == Status.PENDING_ADMIN_APPROVAL,
        )
        .order_by(PendingUpload.detected_at.desc(), PendingUpload.upload_id.desc())
    )
    return list(result.all())


def build_pending_description(upload_data: dict[str, Any]) -> str:
    """Build description for pending upload."""
    new_count = len(upload_data.get("new_files", []))
    modified_count = len(upload_data.get("modified_files", []))
    deleted_count = len(upload_data.get("deleted_files", []))

    parts = []
    if new_count > 0:
        parts.append(f"{new_count} new")
    if modified_count > 0:
        parts.append(f"{modified_count} modified")
    if deleted_count > 0:
        parts.append(f"{deleted_count} deleted")

    files_desc = ", ".join(parts) if parts else "no changes"
    return f"Pending upload: {files_desc} files"


async def mark_upload_processed(
    db: AsyncSession,
    project_id: int,
    branch_name: str,
    user_id: int,
    accepted_commit: str,
) -> None:
    """Mark upload as processed after merge."""
    stmt = select(PendingUpload).where(
        PendingUpload.branch_name == branch_name,
        PendingUpload.project_id == project_id,
        PendingUpload.status == Status.PENDING_ADMIN_APPROVAL,
    )
    result = await db.execute(stmt)
    upload_record = result.scalar_one_or_none()

    if upload_record:
        upload_record.status = Status.RESOLVED
        upload_record.resolved_at = func.now()
        upload_record.resolved_by = user_id
        upload_record.accepted_commit = accepted_commit
        await db.commit()
