"""Invitation CRUD operations - Pure database access layer."""

import secrets
from datetime import UTC, datetime, timedelta
from typing import cast

from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.model.enums import InvitationStatus, ProjectPermission
from app.model.invitation import Invitation
from app.utils.database import DatabaseUtils

# Password context for hashing codes
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

logger = get_logger()


async def delete_project_invitations(db: AsyncSession, project_id: int) -> int:
    logger.info(f"Deleting invitations for project_id={project_id}")
    try:
        count = await DatabaseUtils.bulk_delete(
            db, Invitation, Invitation.project_id == project_id
        )
        logger.info(f"Deleted {count} invitations for project_id={project_id}")
        return count
    except Exception as e:
        logger.error(
            "Failed to delete project invitations; error_type=%s",
            safe_exception_type(e),
        )
        raise


async def create_invitation(
    db: AsyncSession,
    sender_id: int,
    receiver_email: str,
    project_id: int,
    project_permission: ProjectPermission = ProjectPermission.READ,
    expires_in_days: int = 7,
    *,
    commit: bool = True,
) -> tuple[Invitation, str]:
    """Create a new invitation in the database.

    Returns:
        Tuple[Invitation, str]: The created invitation and the raw code for email

    """
    expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

    # Generate a secure random code (independent of invitation_id)
    raw_code = secrets.token_urlsafe(32)  # 32 bytes = 256 bits of entropy
    hashed_code = pwd_context.hash(raw_code)

    invitation = Invitation(
        sender=sender_id,
        receiver_email=receiver_email,
        project_id=project_id,
        project_permission=project_permission,
        status=InvitationStatus.PENDING,
        expires_at=expires_at,
        hashed_code=hashed_code,
    )

    db.add(invitation)
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(invitation)
    return invitation, raw_code


async def get_invitation_by_id(
    db: AsyncSession, invitation_id: int, *, for_update: bool = False
) -> Invitation | None:
    """Retrieve an invitation by ID."""
    query = select(Invitation).filter(Invitation.invitation_id == invitation_id)
    if for_update:
        query = query.with_for_update()
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def get_invitations_by_email(db: AsyncSession, email: str) -> list[Invitation]:
    """Get all invitations for a specific email."""
    result = await db.execute(
        select(Invitation).filter(Invitation.receiver_email == email)
    )
    return list(result.scalars().all())


async def get_pending_invitations_by_email(
    db: AsyncSession, email: str, project_id: int | None = None
) -> list[Invitation]:
    """Get pending invitations for an email, optionally within one project."""
    query = (
        select(Invitation)
        .filter(Invitation.receiver_email == email)
        .filter(Invitation.status == InvitationStatus.PENDING)
        .filter(Invitation.expires_at > datetime.now(UTC))
    )
    if project_id is not None:
        query = query.filter(Invitation.project_id == project_id)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_invitation_status(
    db: AsyncSession,
    invitation_id: int,
    status: InvitationStatus,
    receiver_id: int | None = None,
    *,
    commit: bool = True,
) -> bool:
    """Update invitation status and optionally set receiver_id."""
    invitation = await get_invitation_by_id(db, invitation_id)
    if not invitation:
        return False

    invitation.status = status
    invitation.responded_at = datetime.now(UTC)
    if receiver_id:
        invitation.receiver = receiver_id

    if commit:
        await db.commit()
    else:
        await db.flush()
    return True


async def check_invitation_exists_and_valid(
    db: AsyncSession, invitation_id: int
) -> bool:
    """Check if invitation exists and is still valid."""
    invitation = await get_invitation_by_id(db, invitation_id)
    return (
        invitation is not None
        and invitation.status == InvitationStatus.PENDING
        and invitation.expires_at > datetime.now(UTC)
    )


async def get_invitations_by_sender(
    db: AsyncSession, sender_id: int
) -> list[Invitation]:
    """Get all invitations sent by a specific user."""
    result = await db.execute(select(Invitation).filter(Invitation.sender == sender_id))
    return list(result.scalars().all())


async def get_invitations_by_project(
    db: AsyncSession, project_id: int
) -> list[Invitation]:
    """Get all invitations for a specific project."""
    result = await db.execute(
        select(Invitation).filter(Invitation.project_id == project_id)
    )
    return list(result.scalars().all())


async def expire_old_invitations(db: AsyncSession) -> int:
    """Mark expired invitations as expired and return count."""
    result = await db.execute(
        select(Invitation)
        .filter(Invitation.status == InvitationStatus.PENDING)
        .filter(Invitation.expires_at <= datetime.now(UTC))
    )
    expired_invitations = list(result.scalars().all())
    if not expired_invitations:
        return 0

    updates = [
        {"invitation_id": inv.invitation_id, "status": InvitationStatus.EXPIRED}
        for inv in expired_invitations
    ]
    await DatabaseUtils.bulk_update(db, Invitation, updates, pk_field="invitation_id")
    return len(updates)


async def verify_invitation_code(
    db: AsyncSession, invitation_id: int, raw_code: str
) -> bool:
    """Verify if the provided code matches the invitation's hashed code."""
    invitation = await get_invitation_by_id(db, invitation_id)
    if not invitation:
        return False

    return cast("bool", pwd_context.verify(raw_code, invitation.hashed_code))


async def get_invitation_by_code(db: AsyncSession, raw_code: str) -> Invitation | None:
    """Retrieve an invitation by verifying the raw code against hashed codes."""
    # Get all pending invitations
    result = await db.execute(
        select(Invitation)
        .filter(Invitation.status == InvitationStatus.PENDING)
        .filter(Invitation.expires_at > datetime.now(UTC))
    )
    invitations = list(result.scalars().all())

    # Check each invitation's hashed code against the provided raw code
    for invitation in invitations:
        if pwd_context.verify(raw_code, invitation.hashed_code):
            return invitation

    return None
