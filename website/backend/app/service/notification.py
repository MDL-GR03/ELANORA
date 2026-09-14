"""Notification service layer - Business logic for notifications."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud import notification as notification_crud
from app.crud.notification import get_notification_preference_by_user_id
from app.schema.requests.notification import (
    NotificationCreateRequest,
    NotificationPreferenceUpdateRequest,
)
from app.schema.responses.notification import (
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from app.service.email import EmailService

logger = get_logger()


class NotificationService:
    """Service class for notification-related business logic."""

    @staticmethod
    async def get_user_notifications(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[NotificationResponse]:
        """Get all notifications for a user with pagination."""
        logger.info(f"Getting notifications for user {user_id}")

        notifications = await notification_crud.get_notifications_by_user_id(
            db, user_id, skip, limit
        )

        return [
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ]

    @staticmethod
    async def get_user_unread_notifications(
        db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100
    ) -> list[NotificationResponse]:
        """Get unread notifications for a user with pagination."""
        logger.info(f"Getting unread notifications for user {user_id}")

        notifications = await notification_crud.get_unread_notifications_by_user_id(
            db, user_id, skip, limit
        )

        return [
            NotificationResponse.model_validate(notification)
            for notification in notifications
        ]

    @staticmethod
    async def create_notification(
        db: AsyncSession, notification_data: NotificationCreateRequest
    ) -> NotificationResponse:
        """Create a new notification."""
        logger.info("Creating notification for user_id=%s", notification_data.user_id)

        notification = await notification_crud.create_notification(
            db, notification_data
        )
        await db.commit()

        logger.info(f"Notification {notification.notification_id} created successfully")
        return NotificationResponse.model_validate(notification)

    @staticmethod
    async def mark_notification_read(
        db: AsyncSession, notification_id: int, user_id: int
    ) -> NotificationResponse | None:
        """Mark a notification as read."""
        logger.info(
            f"Marking notification {notification_id} as read for user {user_id}"
        )

        # First verify the notification belongs to the user
        notification = await notification_crud.get_notification_by_id(
            db, notification_id
        )
        if not notification or notification.user_id != user_id:
            logger.warning(
                f"Notification {notification_id} not found or doesn't belong to user {user_id}"
            )
            return None

        updated_notification = await notification_crud.mark_notification_as_read(
            db, notification_id
        )
        if updated_notification:
            await db.commit()
            logger.info(f"Notification {notification_id} marked as read")
            return NotificationResponse.model_validate(updated_notification)

        return None

    @staticmethod
    async def mark_all_notifications_read(db: AsyncSession, user_id: int) -> int:
        """Mark all notifications as read for a user."""
        logger.info(f"Marking all notifications as read for user {user_id}")

        count = await notification_crud.mark_all_notifications_as_read(db, user_id)
        await db.commit()

        logger.info(f"Marked {count} notifications as read for user {user_id}")
        return count

    @staticmethod
    async def delete_notification(
        db: AsyncSession, notification_id: int, user_id: int
    ) -> bool:
        """Delete a notification."""
        logger.info(f"Deleting notification {notification_id} for user {user_id}")

        # First verify the notification belongs to the user
        notification = await notification_crud.get_notification_by_id(
            db, notification_id
        )
        if not notification or notification.user_id != user_id:
            logger.warning(
                f"Notification {notification_id} not found or doesn't belong to user {user_id}"
            )
            return False

        success = await notification_crud.delete_notification(db, notification_id)
        if success:
            await db.commit()
            logger.info(f"Notification {notification_id} deleted successfully")

        return success

    @staticmethod
    async def get_notification_stats(
        db: AsyncSession, user_id: int
    ) -> NotificationStatsResponse:
        """Get notification statistics for a user."""
        logger.info(f"Getting notification stats for user {user_id}")

        stats = await notification_crud.get_notification_stats(db, user_id)
        return NotificationStatsResponse(**stats)

    # Notification Preference Methods

    @staticmethod
    async def get_notification_preference(
        db: AsyncSession, user_id: int
    ) -> NotificationPreferenceResponse:
        """Get notification preferences for a user."""
        logger.info(f"Getting notification preferences for user {user_id}")

        preference = await notification_crud.get_or_create_notification_preference(
            db, user_id
        )
        # The CRUD operation creates the default row when it does not exist.
        # Persist that default instead of losing it when the request session closes.
        await db.commit()
        return NotificationPreferenceResponse.model_validate(preference)

    @staticmethod
    async def update_notification_preference(
        db: AsyncSession,
        user_id: int,
        preference_data: NotificationPreferenceUpdateRequest,
    ) -> NotificationPreferenceResponse:
        """Update notification preferences for a user."""
        logger.info(f"Updating notification preferences for user {user_id}")

        preference = await notification_crud.update_notification_preference(
            db, user_id, preference_data
        )
        await db.commit()
        await db.refresh(preference)

        logger.info(f"Notification preferences updated for user {user_id}")
        return NotificationPreferenceResponse.model_validate(preference)

    @staticmethod
    async def create_user_preference(
        db: AsyncSession, user_id: int, email_enabled: bool = True
    ) -> NotificationPreferenceResponse:
        """Create default notification preferences for a new user."""
        logger.info(f"Creating default notification preferences for user {user_id}")

        preference = await notification_crud.create_notification_preference(
            db, user_id, email_enabled
        )

        logger.info(f"Default notification preferences created for user {user_id}")
        return NotificationPreferenceResponse.model_validate(preference)

    # Helper methods for creating common notification types

    @staticmethod
    async def create_project_invitation_notification(
        db: AsyncSession,
        user_id: int,
        project_name: str,
        inviter_name: str,
        project_id: int,
    ) -> NotificationResponse:
        """Create a notification for project invitation."""
        notification_data = NotificationCreateRequest(
            user_id=user_id,
            title="Nouvelle invitation au projet",
            message=f"{inviter_name} vous a invité à rejoindre le projet '{project_name}'.",
            action_url="/projects",
        )

        return await NotificationService.create_notification(db, notification_data)

    @staticmethod
    async def create_project_role_change_notification(
        db: AsyncSession,
        user_id: int,
        project_name: str,
        new_role: str,
        project_id: int,
        admin_name: str,
    ) -> NotificationResponse:
        """Create a notification for project role change."""
        notification_data = NotificationCreateRequest(
            user_id=user_id,
            title="Rôle dans le projet modifié",
            message=f"Votre rôle dans le projet '{project_name}' a été modifié à '{new_role}' par {admin_name}.",
            action_url="/projects",
        )

        return await NotificationService.create_notification(db, notification_data)

    @staticmethod
    async def create_project_member_joined_notification(
        db: AsyncSession,
        admin_user_id: int,
        project_name: str,
        new_member_name: str,
        project_id: int,
    ) -> NotificationResponse:
        """Create a notification for admins when a new member joins a project."""
        notification_data = NotificationCreateRequest(
            user_id=admin_user_id,
            title="Nouveau membre dans le projet",
            message=f"{new_member_name} a rejoint le projet '{project_name}'.",
            action_url=f"/projects/{project_id}/configuration",
        )

        return await NotificationService.create_notification(db, notification_data)

    @staticmethod
    async def create_comment_notification(
        db: AsyncSession,
        user_id: int,
        commenter_name: str,
        project_name: str,
        project_id: int,
    ) -> NotificationResponse:
        """Create a notification for new comment."""
        notification_data = NotificationCreateRequest(
            user_id=user_id,
            title="Nouveau commentaire",
            message=f"{commenter_name} a ajouté un commentaire dans le projet '{project_name}'.",
            action_url="/projects",
        )

        return await NotificationService.create_notification(db, notification_data)

    @staticmethod
    async def create_conflict_resolution_notification(
        db: AsyncSession,
        user_id: int,
        resolver_name: str,
        project_name: str,
        project_id: int,
    ) -> NotificationResponse:
        """Create a notification for conflict resolution."""
        notification_data = NotificationCreateRequest(
            user_id=user_id,
            title="Conflit résolu",
            message=f"{resolver_name} a résolu un conflit dans le projet '{project_name}'.",
            action_url="/conflicts",
        )

        return await NotificationService.create_notification(db, notification_data)

    @staticmethod
    async def send_role_change_notification_and_email(
        db: AsyncSession,
        user_id: int,
        user_email: str,
        username: str,
        project_name: str,
        new_role: str,
        project_id: int,
        admin_name: str,
        language: str = "fr",
    ) -> tuple[NotificationResponse, bool]:
        """Create a notification and send email for role change if user preferences allow it."""
        # Create notification
        notification = (
            await NotificationService.create_project_role_change_notification(
                db=db,
                user_id=user_id,
                project_name=project_name,
                new_role=new_role,
                project_id=project_id,
                admin_name=admin_name,
            )
        )

        # Check if user wants email notifications
        email_sent = False
        try:
            preference = await get_notification_preference_by_user_id(db, user_id)
            if preference and preference.email_enabled:
                email_service = EmailService()
                email_sent = await email_service.send_role_change_email(
                    email=user_email,
                    username=username,
                    project_name=project_name,
                    new_role=new_role,
                    admin_name=admin_name,
                    language=language,
                )
        except Exception as e:
            logger.warning(
                "Failed to send a role-change email; error_type=%s",
                safe_exception_type(e),
            )

        return notification, email_sent
