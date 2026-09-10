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
    """Build a concise file-change summary for a contribution."""
    files = upload_data.get("upload_data", upload_data)
    counts = (
        (len(files.get("new_files", [])), "new"),
        (len(files.get("modified_files", [])), "modified"),
        (len(files.get("deleted_files", [])), "deleted"),
    )
    parts = [
        f"{count} {kind} {'file' if count == 1 else 'files'}"
        for count, kind in counts
        if count
    ]
    return ", ".join(parts) if parts else "No file changes detected"


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
