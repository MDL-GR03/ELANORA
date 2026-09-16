"""Accepting or rejecting an invitation, and the membership it creates."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.invitation import get_invitation_by_id, update_invitation_status
from app.crud.project import add_user_to_project, user_in_project
from app.crud.user import get_user_by_id
from app.model.enums import InvitationStatus
from app.service.invitation_notifications import notify_project_admins_member_joined

logger = get_logger()


async def accept_invitation(  # noqa: PLR0911 - explicit validation exits
    db: AsyncSession,
    invitation_id: int,
    user_id: int,
    *,
    commit: bool = True,
) -> bool:
    """Mark an invitation as accepted and add user to project."""
    try:
        # Get invitation details first
        invitation = await get_invitation_by_id(db, invitation_id, for_update=True)
        if not invitation:
            logger.warning("Invitation not found")
            return False

        project_id = invitation.project_id

        if (
            invitation.status != InvitationStatus.PENDING
            or invitation.expires_at <= datetime.now(UTC)
        ):
            logger.info("Invitation cannot be accepted in its current state")
            return False

        user = await get_user_by_id(db, user_id)
        if (
            user is None
            or user.email.strip().casefold()
            != invitation.receiver_email.strip().casefold()
        ):
            logger.warning("Invitation recipient mismatch")
            return False

        existing_membership = await user_in_project(db, user_id, project_id)
        if existing_membership:
            logger.info("Invitation recipient is already a project member")
            return False

        try:
            await add_user_to_project(
                db=db,
                user_id=user_id,
                project_id=project_id,
                permission=invitation.project_permission,
                commit=False,
            )
            success = await update_invitation_status(
                db=db,
                invitation_id=invitation_id,
                status=InvitationStatus.ACCEPTED,
                receiver_id=user_id,
                commit=False,
            )
            if not success:
                await db.rollback()
                return False

            if not commit:
                await db.flush()
                return True

            await db.commit()
            logger.info("User added to project via invitation")

            await notify_project_admins_member_joined(db, project_id, user)

            return True
        except Exception as project_error:
            await db.rollback()
            logger.error(
                "Failed to accept invitation atomically; error_type=%s",
                safe_exception_type(project_error),
            )
            return False

    except Exception as e:
        logger.error(
            "Failed to accept invitation; error_type=%s", safe_exception_type(e)
        )
        return False


async def accept_invitation_by_user(
    db: AsyncSession,
    invitation_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Accept an invitation by an existing user."""
    try:
        # Get invitation details
        invitation = await get_invitation_by_id(db, invitation_id)
        if not invitation:
            return {"success": False, "message": "Invitation not found"}

        # Check if invitation is still pending
        if invitation.status != InvitationStatus.PENDING:
            return {"success": False, "message": "Invitation is no longer pending"}

        # Verify the user matches the invitation email
        user = await get_user_by_id(db, user_id)
        if not user or user.email != invitation.receiver_email:
            return {
                "success": False,
                "message": "User email does not match invitation",
            }

        # Check if user is already in the project
        existing_membership = await user_in_project(db, user_id, invitation.project_id)
        if existing_membership:
            # Mark invitation as accepted anyway
            await update_invitation_status(
                db=db,
                invitation_id=invitation_id,
                status=InvitationStatus.ACCEPTED,
                receiver_id=user_id,
            )
            return {
                "success": False,
                "message": "You are already a member of this project",
            }

        # Accept the invitation
        success = await accept_invitation(
            db=db,
            invitation_id=invitation_id,
            user_id=user_id,
        )

        if success:
            logger.info("Invitation accepted by existing user")
            return {"success": True, "message": "Invitation accepted successfully"}
        else:
            return {"success": False, "message": "Failed to accept invitation"}

    except Exception as e:
        logger.error(
            "Failed to accept invitation by user; error_type=%s",
            safe_exception_type(e),
        )
        return {"success": False, "message": "Internal server error"}


async def reject_invitation_by_user(
    db: AsyncSession,
    invitation_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Reject an invitation by an existing user."""
    try:
        # Get invitation details
        invitation = await get_invitation_by_id(db, invitation_id)
        if not invitation:
            return {"success": False, "message": "Invitation not found"}

        # Check if invitation is still pending
        if invitation.status != InvitationStatus.PENDING:
            return {"success": False, "message": "Invitation is no longer pending"}

        # Verify the user matches the invitation email
        user = await get_user_by_id(db, user_id)
        if not user or user.email != invitation.receiver_email:
            return {
                "success": False,
                "message": "User email does not match invitation",
            }

        # Reject the invitation
        success = await update_invitation_status(
            db=db,
            invitation_id=invitation_id,
            status=InvitationStatus.REJECTED,
            receiver_id=user_id,
        )

        if success:
            logger.info("Invitation rejected by existing user")
            return {"success": True, "message": "Invitation rejected successfully"}
        else:
            return {"success": False, "message": "Failed to reject invitation"}

    except Exception as e:
        logger.error(
            "Failed to reject invitation by user; error_type=%s",
            safe_exception_type(e),
        )
        return {"success": False, "message": "Internal server error"}
