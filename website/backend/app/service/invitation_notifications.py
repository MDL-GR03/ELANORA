"""Telling people about invitations, without ever failing the invitation itself."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.notification import (
    create_notification,
    get_notification_preference_by_user_id,
)
from app.crud.project import get_project_admins_and_owners, get_project_by_id
from app.model.user import User
from app.schema.requests.notification import NotificationCreateRequest
from app.service.notification import NotificationService
from app.service.outbox import enqueue_existing_user_invitation_email

logger = get_logger()


async def create_invitation_notification(
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
            message = (
                f"{sender_name} vous a invité à rejoindre le projet '{project_name}'"
            )
        else:
            title = "New project invitation"
            message = f"{sender_name} invited you to join the project '{project_name}'"

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


async def queue_invitation_email_if_enabled(
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
            logger.info("Invitation email skipped because notifications are disabled")
            return (
                True  # Return True because the operation succeeded (just no email sent)
            )

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


async def create_member_joined_notification(
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
                    await create_member_joined_notification(
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
