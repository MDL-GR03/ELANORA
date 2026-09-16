"""Reading invitations: what a person may see before deciding."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.invitation import (
    get_invitation_by_code,
    get_invitation_by_id,
    get_invitations_by_email,
    get_invitations_by_project,
    get_invitations_by_sender,
)
from app.crud.project import get_project_by_id, user_in_project
from app.crud.user import get_user_by_id, get_user_by_username_or_email
from app.model.enums import InvitationStatus
from app.model.invitation import Invitation
from app.schema.responses.invitation import (
    InvitationListResponse,
    InvitationResponse,
    InvitationValidationResponse,
)

logger = get_logger()


async def invitation_response(
    db: AsyncSession,
    invitation: Invitation,
) -> InvitationResponse:
    """Convert invitation model to response format."""
    # Get sender information
    sender = await get_user_by_id(db, invitation.sender)
    sender_username = sender.username if sender else None

    # Get project information
    project_name = None
    if invitation.project_id:
        project = await get_project_by_id(db, invitation.project_id)
        project_name = project.project_name if project else None

    return InvitationResponse(
        invitation_id=invitation.invitation_id,
        receiver_email=invitation.receiver_email,
        project_id=invitation.project_id,
        project_permission=invitation.project_permission,
        status=invitation.status,
        created_at=invitation.created_at,
        expires_at=invitation.expires_at,
        responded_at=invitation.responded_at,
        sender_username=sender_username,
        project_name=project_name,
    )


async def validate_invitation(
    db: AsyncSession,
    invitation_code: str,
) -> InvitationValidationResponse:
    """Validate an invitation code without changing membership or state."""
    try:
        # Find invitation by code
        invitation = await get_invitation_by_code(db, invitation_code)

        if not invitation:
            return InvitationValidationResponse(
                valid=False, message="Invalid invitation code"
            )

        # Check if invitation is already accepted
        if invitation.status == InvitationStatus.ACCEPTED:
            return InvitationValidationResponse(
                valid=False, message="This invitation has already been accepted"
            )

        # Check if invitation is expired or rejected
        if invitation.status in [
            InvitationStatus.EXPIRED,
            InvitationStatus.REJECTED,
        ]:
            return InvitationValidationResponse(
                valid=False, message="This invitation is no longer valid"
            )

        # Validation is deliberately read-only. Existing users accept through the
        # authenticated decision endpoint; new users redeem the code at registration.
        if invitation.receiver_email:
            existing_user = await get_user_by_username_or_email(
                db, invitation.receiver_email
            )

            if existing_user:
                existing_membership = await user_in_project(
                    db, existing_user.user_id, invitation.project_id
                )
                if existing_membership:
                    return InvitationValidationResponse(
                        valid=False,
                        message="You are already a member of this project",
                        user_exists=True,
                    )
                response = await invitation_response(db, invitation)
                return InvitationValidationResponse(
                    valid=True,
                    invitation=response,
                    message="Sign in to review this invitation",
                    user_exists=True,
                )

        # Convert to response format for new user registration
        response = await invitation_response(db, invitation)

        return InvitationValidationResponse(
            valid=True,
            invitation=response,
            message="Invitation is valid",
            user_exists=False,
        )

    except Exception as e:
        logger.error(
            "Failed to validate invitation; error_type=%s",
            safe_exception_type(e),
        )
        return InvitationValidationResponse(
            valid=False, message="Internal server error"
        )


async def user_invitations(
    db: AsyncSession,
    email: str,
) -> InvitationListResponse:
    """Get all invitations for a user by email."""
    try:
        invitations = await get_invitations_by_email(db, email)
        invitation_responses = []

        for invitation in invitations:
            response = await invitation_response(db, invitation)
            invitation_responses.append(response)

        return InvitationListResponse(
            invitations=invitation_responses, total=len(invitation_responses)
        )

    except Exception as e:
        logger.error(
            "Failed to get user invitations; error_type=%s",
            safe_exception_type(e),
        )
        return InvitationListResponse(invitations=[], total=0)


async def sent_invitations(
    db: AsyncSession,
    sender_id: int,
) -> InvitationListResponse:
    """Get all invitations sent by a user."""
    try:
        invitations = await get_invitations_by_sender(db, sender_id)
        invitation_responses = []

        for invitation in invitations:
            response = await invitation_response(db, invitation)
            invitation_responses.append(response)

        return InvitationListResponse(
            invitations=invitation_responses, total=len(invitation_responses)
        )

    except Exception as e:
        logger.error(
            "Failed to get sent invitations; error_type=%s",
            safe_exception_type(e),
        )
        return InvitationListResponse(invitations=[], total=0)


async def project_invitations(
    db: AsyncSession,
    project_id: int,
) -> InvitationListResponse:
    """Get all invitations for a specific project."""
    try:
        # Check if project exists
        project = await get_project_by_id(db, project_id)
        if not project:
            logger.warning("Invitation project not found")
            return InvitationListResponse(invitations=[], total=0)

        # Get invitations for this project
        invitations = await get_invitations_by_project(db, project_id)
        invitation_responses = []

        for invitation in invitations:
            response = await invitation_response(db, invitation)
            invitation_responses.append(response)

        return InvitationListResponse(
            invitations=invitation_responses, total=len(invitation_responses)
        )

    except Exception as e:
        logger.error(
            "Failed to get project invitations; error_type=%s",
            safe_exception_type(e),
        )
        return InvitationListResponse(invitations=[], total=0)


async def invitation_details_for_user(
    db: AsyncSession,
    invitation_id: int,
    user_id: int,
) -> dict[str, Any]:
    """Get invitation details for a user to make accept/reject decision."""
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
                "message": "This invitation is not for your account",
            }

        # Get project details
        project = await get_project_by_id(db, invitation.project_id)
        if not project:
            return {"success": False, "message": "Project not found"}

        # Get sender details
        sender = await get_user_by_id(db, invitation.sender)
        sender_name = f"{sender.first_name} {sender.last_name}" if sender else "Unknown"

        return {
            "success": True,
            "invitation_id": invitation.invitation_id,
            "sender_name": sender_name,
            "project_name": project.project_name,
            "expires_at": invitation.expires_at.isoformat()
            if invitation.expires_at
            else None,
            "created_at": invitation.created_at.isoformat(),
        }

    except Exception as e:
        logger.error(
            "Failed to get invitation details; error_type=%s",
            safe_exception_type(e),
        )
        return {"success": False, "message": "Internal server error"}
