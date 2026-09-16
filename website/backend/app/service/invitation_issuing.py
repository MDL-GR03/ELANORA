"""Issuing invitations: sending, resending and cancelling them."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.invitation import (
    create_invitation,
    get_invitation_by_id,
    get_pending_invitations_by_email,
    update_invitation_status,
)
from app.crud.project import get_project_by_id, get_project_by_name, user_in_project
from app.crud.user import get_user_by_id, get_user_by_username_or_email
from app.model.enums import InvitationStatus
from app.schema.requests.invitation import InvitationSendRequest
from app.schema.responses.invitation import InvitationSendResponse
from app.service.email import EmailService
from app.service.invitation_notifications import (
    create_invitation_notification,
    queue_invitation_email_if_enabled,
)

logger = get_logger()


async def send_invitation(
    db: AsyncSession,
    email_service: EmailService,
    sender_id: int,
    request: InvitationSendRequest,
) -> InvitationSendResponse:
    """Send an invitation email to a user."""
    try:
        # Get sender information
        sender = await get_user_by_id(db, sender_id)
        if not sender:
            return InvitationSendResponse(success=False, message="Sender not found")

        # Get project information
        project = await get_project_by_name(db, request.project_name)
        if not project:
            return InvitationSendResponse(success=False, message="Project not found")

        # Check if receiver already exists as a user
        existing_user = await get_user_by_username_or_email(db, request.receiver_email)

        # Check for existing invitations for this email
        existing = await get_pending_invitations_by_email(
            db, request.receiver_email, project_id=project.project_id
        )
        if existing:
            return InvitationSendResponse(
                success=False,
                message="An active invitation already exists for this email.",
            )

        # If user exists, check if they're already in the project
        if existing_user:
            existing_membership = await user_in_project(
                db, existing_user.user_id, project.project_id
            )
            if existing_membership:
                return InvitationSendResponse(
                    success=False,
                    message="User is already a member of this project.",
                )

        # Create invitation in database
        invitation, raw_code = await create_invitation(
            db=db,
            sender_id=sender_id,
            receiver_email=request.receiver_email,
            project_id=project.project_id,
            project_permission=request.project_permission,
            expires_in_days=request.expires_in_days,
            commit=False,
        )

        # Send different email based on whether user exists
        language = request.language or "en"
        if existing_user:
            # Create notification for existing user
            await create_invitation_notification(
                db=db,
                user_id=existing_user.user_id,
                invitation_id=invitation.invitation_id,
                sender_name=f"{sender.first_name} {sender.last_name}",
                project_name=project.project_name,
                language=language,
            )

            # Check user's email preferences and send email if enabled
            email_sent = await queue_invitation_email_if_enabled(
                db=db,
                user_id=existing_user.user_id,
                email=request.receiver_email,
                invitation_id=invitation.invitation_id,
                sender_name=f"{sender.first_name} {sender.last_name}",
                project_name=project.project_name,
                custom_message=request.message,
                language=language,
            )
        else:
            # Send new user invitation email with registration link
            email_sent = await email_service.send_invitation_email(
                email=request.receiver_email,
                invitation_code=raw_code,
                sender_name=f"{sender.first_name} {sender.last_name}",
                project_name=project.project_name,
                custom_message=request.message,
                language=language,
            )

        if email_sent:
            logger.info("Invitation sent successfully")
            return InvitationSendResponse(
                success=True,
                message="Invitation sent successfully",
                invitation_id=invitation.invitation_id,
                invitation_code=raw_code if not existing_user else None,
            )
        else:
            await db.rollback()
            return InvitationSendResponse(
                success=False,
                message="Failed to send invitation email",
            )

    except Exception as e:
        await db.rollback()
        logger.error("Failed to send invitation; error_type=%s", safe_exception_type(e))
        return InvitationSendResponse(success=False, message="Internal server error")


async def resend_invitation(
    db: AsyncSession,
    email_service: EmailService,
    invitation_id: int,
    sender_id: int,
) -> dict[str, Any]:
    """Resend an invitation email."""
    try:
        # Get invitation details
        invitation = await get_invitation_by_id(db, invitation_id)
        if not invitation:
            return {"success": False, "message": "Invitation not found"}

        # Verify the sender owns this invitation
        if invitation.sender != sender_id:
            return {
                "success": False,
                "message": "You can only resend invitations you sent",
            }

        # Check if invitation is still pending
        if invitation.status != InvitationStatus.PENDING:
            return {
                "success": False,
                "message": "Can only resend pending invitations",
            }

        # Get sender and project information
        sender = await get_user_by_id(db, sender_id)
        if not sender:
            return {"success": False, "message": "Sender not found"}

        project = await get_project_by_id(db, invitation.project_id)
        if not project:
            return {"success": False, "message": "Project not found"}

        # Check if receiver is an existing user
        existing_user = await get_user_by_username_or_email(
            db, invitation.receiver_email
        )

        # Send appropriate email based on user existence
        email_sent = False
        if existing_user:
            # Send existing user invitation email with accept/reject buttons
            email_sent = await email_service.send_existing_user_invitation_email(
                email=invitation.receiver_email,
                invitation_id=invitation.invitation_id,
                sender_name=f"{sender.first_name} {sender.last_name}",
                project_name=project.project_name,
                custom_message="This is a reminder invitation.",
                language="en",  # You might want to store language in invitation
            )
        else:
            # For new users, create a new invitation with new code
            _, raw_code = await create_invitation(
                db=db,
                sender_id=sender_id,
                receiver_email=invitation.receiver_email,
                project_id=invitation.project_id,
                project_permission=invitation.project_permission,
                expires_in_days=7,  # Reset expiration
            )

            # Deactivate old invitation
            await update_invitation_status(
                db=db,
                invitation_id=invitation_id,
                status=InvitationStatus.EXPIRED,
            )

            # Send new user invitation email with registration link
            email_sent = await email_service.send_invitation_email(
                email=invitation.receiver_email,
                invitation_code=raw_code,
                sender_name=f"{sender.first_name} {sender.last_name}",
                project_name=project.project_name,
                custom_message="This is a reminder invitation.",
                language="en",
            )

        # Handle result for both existing and new users
        if email_sent:
            if existing_user:
                logger.info("Invitation resent successfully")
            else:
                logger.info("Invitation resent with a new code")

            return {"success": True, "message": "Invitation resent successfully"}

        return {"success": False, "message": "Failed to send invitation email"}

    except Exception as e:
        logger.error(
            "Failed to resend invitation; error_type=%s",
            safe_exception_type(e),
        )
        return {"success": False, "message": "Internal server error"}


async def cancel_invitation(
    db: AsyncSession,
    invitation_id: int,
    sender_id: int,
) -> dict[str, Any]:
    """Cancel an invitation."""
    try:
        # Get invitation details
        invitation = await get_invitation_by_id(db, invitation_id)
        if not invitation:
            return {"success": False, "message": "Invitation not found"}

        # Verify the sender owns this invitation
        if invitation.sender != sender_id:
            return {
                "success": False,
                "message": "You can only cancel invitations you sent",
            }

        # Check if invitation is still pending
        if invitation.status != InvitationStatus.PENDING:
            return {
                "success": False,
                "message": "Can only cancel pending invitations",
            }

        # Update invitation status to cancelled
        success = await update_invitation_status(
            db=db,
            invitation_id=invitation_id,
            status=InvitationStatus.EXPIRED,  # Using EXPIRED as "cancelled"
        )

        if success:
            logger.info("Invitation cancelled successfully")
            return {"success": True, "message": "Invitation cancelled successfully"}
        else:
            return {"success": False, "message": "Failed to cancel invitation"}

    except Exception as e:
        logger.error(
            "Failed to cancel invitation; error_type=%s",
            safe_exception_type(e),
        )
        return {"success": False, "message": "Internal server error"}
