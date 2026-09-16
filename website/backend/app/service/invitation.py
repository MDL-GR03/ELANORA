"""Invitation use cases for local project collaboration.

The work lives in four modules, one per use case: issuing invitations,
deciding on them, reading them, and telling people about them.
``InvitationService`` remains the entry point its callers already use.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User
from app.schema.requests.invitation import InvitationSendRequest
from app.schema.responses.invitation import (
    InvitationListResponse,
    InvitationSendResponse,
    InvitationValidationResponse,
)
from app.service import (
    invitation_decisions,
    invitation_issuing,
    invitation_notifications,
    invitation_queries,
)
from app.service.email import EmailService


class InvitationService:
    """Entry point for everything an invitation can do."""

    def __init__(self) -> None:
        self.email_service = EmailService()

    async def send_invitation(
        self,
        db: AsyncSession,
        sender_id: int,
        request: InvitationSendRequest,
    ) -> InvitationSendResponse:
        """Send an invitation email to a user."""
        return await invitation_issuing.send_invitation(
            db, self.email_service, sender_id, request
        )

    async def resend_invitation(
        self, db: AsyncSession, invitation_id: int, sender_id: int
    ) -> dict[str, Any]:
        """Resend an invitation email."""
        return await invitation_issuing.resend_invitation(
            db, self.email_service, invitation_id, sender_id
        )

    async def cancel_invitation(
        self, db: AsyncSession, invitation_id: int, sender_id: int
    ) -> dict[str, Any]:
        """Cancel an invitation."""
        return await invitation_issuing.cancel_invitation(db, invitation_id, sender_id)

    async def validate_invitation(
        self, db: AsyncSession, invitation_code: str
    ) -> InvitationValidationResponse:
        """Validate an invitation code without changing membership or state."""
        return await invitation_queries.validate_invitation(db, invitation_code)

    async def accept_invitation(
        self,
        db: AsyncSession,
        invitation_id: int,
        user_id: int,
        *,
        commit: bool = True,
    ) -> bool:
        """Mark an invitation as accepted and add user to project."""
        return await invitation_decisions.accept_invitation(
            db, invitation_id, user_id, commit=commit
        )

    async def accept_invitation_by_user(
        self, db: AsyncSession, invitation_id: int, user_id: int
    ) -> dict[str, Any]:
        """Accept an invitation by an existing user."""
        return await invitation_decisions.accept_invitation_by_user(
            db, invitation_id, user_id
        )

    async def reject_invitation_by_user(
        self, db: AsyncSession, invitation_id: int, user_id: int
    ) -> dict[str, Any]:
        """Reject an invitation by an existing user."""
        return await invitation_decisions.reject_invitation_by_user(
            db, invitation_id, user_id
        )

    async def get_user_invitations(
        self, db: AsyncSession, email: str
    ) -> InvitationListResponse:
        """Get all invitations for a user by email."""
        return await invitation_queries.user_invitations(db, email)

    async def get_sent_invitations(
        self, db: AsyncSession, sender_id: int
    ) -> InvitationListResponse:
        """Get all invitations sent by a user."""
        return await invitation_queries.sent_invitations(db, sender_id)

    async def get_project_invitations(
        self, db: AsyncSession, project_id: int
    ) -> InvitationListResponse:
        """Get all invitations for a specific project."""
        return await invitation_queries.project_invitations(db, project_id)

    async def get_invitation_details_for_user(
        self, db: AsyncSession, invitation_id: int, user_id: int
    ) -> dict[str, Any]:
        """Get invitation details for a user to make accept/reject decision."""
        return await invitation_queries.invitation_details_for_user(
            db, invitation_id, user_id
        )

    @staticmethod
    async def notify_project_admins_member_joined(
        db: AsyncSession, project_id: int, user: User
    ) -> None:
        """Best-effort notification after membership has committed."""
        await invitation_notifications.notify_project_admins_member_joined(
            db, project_id, user
        )
