"""Invitation use cases for local project collaboration."""

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.invitation import (
    create_invitation,
    get_invitation_by_code,
    get_invitation_by_id,
    get_invitations_by_email,
    get_invitations_by_project,
    get_invitations_by_sender,
    get_pending_invitations_by_email,
    update_invitation_status,
)
from app.crud.notification import (
    create_notification,
    get_notification_preference_by_user_id,
)
from app.crud.project import (
    add_user_to_project,
    get_project_admins_and_owners,
    get_project_by_id,
    get_project_by_name,
    user_in_project,
)
from app.crud.user import get_user_by_id, get_user_by_username_or_email
from app.model.enums import InvitationStatus
from app.model.invitation import Invitation
from app.model.user import User
from app.schema.requests.invitation import InvitationSendRequest
from app.schema.requests.notification import NotificationCreateRequest
from app.schema.responses.invitation import (
    InvitationListResponse,
    InvitationResponse,
    InvitationSendResponse,
    InvitationValidationResponse,
)
from app.service.email import EmailService
from app.service.notification import NotificationService
from app.service.outbox import enqueue_existing_user_invitation_email

# Get logger for this module
logger = get_logger()


class InvitationService:
    """Service for managing invitations."""

    def __init__(self) -> None:
        self.email_service = EmailService()

    async def send_invitation(
        self,
        db: AsyncSession,
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
                return InvitationSendResponse(
                    success=False, message="Project not found"
                )

            # Check if receiver already exists as a user
            existing_user = await get_user_by_username_or_email(
                db, request.receiver_email
            )

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
                await self._create_invitation_notification(
                    db=db,
                    user_id=existing_user.user_id,
                    invitation_id=invitation.invitation_id,
                    sender_name=f"{sender.first_name} {sender.last_name}",
                    project_name=project.project_name,
                    language=language,
                )

                # Check user's email preferences and send email if enabled
                email_sent = await self._queue_invitation_email_if_enabled(
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
                email_sent = await self.email_service.send_invitation_email(
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
            logger.error(
                "Failed to send invitation; error_type=%s", safe_exception_type(e)
            )
            return InvitationSendResponse(
                success=False, message="Internal server error"
            )

    async def validate_invitation(
        self,
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
                    invitation_response = await self._convert_to_response(
                        db, invitation
                    )
                    return InvitationValidationResponse(
                        valid=True,
                        invitation=invitation_response,
                        message="Sign in to review this invitation",
                        user_exists=True,
                    )

            # Convert to response format for new user registration
            invitation_response = await self._convert_to_response(db, invitation)

            return InvitationValidationResponse(
                valid=True,
                invitation=invitation_response,
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

    async def accept_invitation(  # noqa: PLR0911 - explicit validation exits
        self,
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
                or invitation.expires_at <= datetime.now()
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

                await self.notify_project_admins_member_joined(db, project_id, user)

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

    async def get_user_invitations(
        self,
        db: AsyncSession,
        email: str,
    ) -> InvitationListResponse:
        """Get all invitations for a user by email."""
        try:
            invitations = await get_invitations_by_email(db, email)
            invitation_responses = []

            for invitation in invitations:
                response = await self._convert_to_response(db, invitation)
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

    async def get_sent_invitations(
        self,
        db: AsyncSession,
        sender_id: int,
    ) -> InvitationListResponse:
        """Get all invitations sent by a user."""
        try:
            invitations = await get_invitations_by_sender(db, sender_id)
            invitation_responses = []

            for invitation in invitations:
                response = await self._convert_to_response(db, invitation)
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

    async def get_project_invitations(
        self,
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
                response = await self._convert_to_response(db, invitation)
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

    async def _convert_to_response(
        self,
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

    async def accept_invitation_by_user(
        self,
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
            existing_membership = await user_in_project(
                db, user_id, invitation.project_id
            )
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
            success = await self.accept_invitation(
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
        self,
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

    async def resend_invitation(
        self,
        db: AsyncSession,
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
                email_sent = (
                    await self.email_service.send_existing_user_invitation_email(
                        email=invitation.receiver_email,
                        invitation_id=invitation.invitation_id,
                        sender_name=f"{sender.first_name} {sender.last_name}",
                        project_name=project.project_name,
                        custom_message="This is a reminder invitation.",
                        language="en",  # You might want to store language in invitation
                    )
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
                email_sent = await self.email_service.send_invitation_email(
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
        self,
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

    async def _create_invitation_notification(
        self,
        db: AsyncSession,
        user_id: int,
        invitation_id: int,
        sender_name: str,
        project_name: str,
        language: str = "en",
    ) -> None:
        """Create a notification for project invitation."""
        try:
            # Create notification with a link to the invitation response page
            action_url = f"/invitation/respond/{invitation_id}"

            # Set title and message based on language
            if language.lower() == "fr":
                title = "Nouvelle invitation au projet"
                message = f"{sender_name} vous a invité à rejoindre le projet '{project_name}'"
            else:
                title = "New project invitation"
                message = (
                    f"{sender_name} invited you to join the project '{project_name}'"
                )

            await create_notification(
                db=db,
                notification_data=NotificationCreateRequest(
                    user_id=user_id,
                    title=title,
                    message=message,
                    action_url=action_url,
                ),
            )

            # Don't commit here - let the main transaction handle it
            await db.flush()  # Just flush to get the notification_id

            logger.info("Invitation notification created")
        except Exception as e:
            logger.error(
                "Failed to create invitation notification; error_type=%s",
                safe_exception_type(e),
            )

    async def _queue_invitation_email_if_enabled(
        self,
        db: AsyncSession,
        user_id: int,
        email: str,
        invitation_id: int,
        sender_name: str,
        project_name: str,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        """Queue invitation email if the recipient enabled email notifications."""
        try:
            # Check user's email preferences
            preferences = await get_notification_preference_by_user_id(db, user_id)

            # If preferences don't exist or email is disabled, don't send email
            if not preferences or not preferences.email_enabled:
                logger.info(
                    "Invitation email skipped because notifications are disabled"
                )
                return True  # Return True because the operation succeeded (just no email sent)

            await enqueue_existing_user_invitation_email(
                db,
                email=email,
                invitation_id=invitation_id,
                sender_name=sender_name,
                project_name=project_name,
                custom_message=custom_message,
                language=language,
            )
            logger.info("Invitation email queued")
            return True

        except Exception as e:
            logger.error(
                "Failed to evaluate or queue invitation email; error_type=%s",
                safe_exception_type(e),
            )
            return False

    async def get_invitation_details_for_user(
        self,
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
            sender_name = (
                f"{sender.first_name} {sender.last_name}" if sender else "Unknown"
            )

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

    @staticmethod
    async def _create_member_joined_notification(
        db: AsyncSession,
        admin_user_id: int,
        project_name: str,
        new_member_name: str,
        project_id: int,
    ) -> None:
        """Create notification for admin when new member joins project."""
        try:
            await NotificationService.create_project_member_joined_notification(
                db=db,
                admin_user_id=admin_user_id,
                project_name=project_name,
                new_member_name=new_member_name,
                project_id=project_id,
            )

            logger.info("Created member joined notification")
        except Exception as e:
            logger.error(
                "Failed to create member joined notification; error_type=%s",
                safe_exception_type(e),
            )

    @staticmethod
    async def notify_project_admins_member_joined(
        db: AsyncSession, project_id: int, user: User
    ) -> None:
        """Best-effort notification after membership has committed."""
        try:
            project = await get_project_by_id(db, project_id)
            if project:
                admin_user_ids = await get_project_admins_and_owners(db, project_id)
                for admin_user_id in admin_user_ids:
                    if admin_user_id != user.user_id:
                        await InvitationService._create_member_joined_notification(
                            db=db,
                            admin_user_id=admin_user_id,
                            project_name=project.project_name,
                            new_member_name=f"{user.first_name} {user.last_name}",
                            project_id=project_id,
                        )
                await db.commit()
        except Exception as notify_error:
            await db.rollback()
            logger.warning(
                "Failed to notify project administrators; error_type=%s",
                safe_exception_type(notify_error),
            )
