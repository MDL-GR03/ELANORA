"""Notification API endpoints."""

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep, get_user_dep
from app.model.user import User
from app.schema.requests.notification import (
    NotificationCreateRequest,
    NotificationPreferenceUpdateRequest,
    NotificationUpdateRequest,
)
from app.schema.responses.notification import (
    NotificationPreferenceResponse,
    NotificationResponse,
    NotificationStatsResponse,
)
from app.service.notification import NotificationService

router = APIRouter()


@router.get("/", response_model=list[NotificationResponse])
async def get_notifications(
    skip: int = Query(0, ge=0, description="Number of notifications to skip"),
    limit: int = Query(
        100, ge=1, le=1000, description="Maximum number of notifications to return"
    ),
    unread_only: bool = Query(
        False, description="If true, only return unread notifications"
    ),
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Get notifications for the current user."""
    if unread_only:
        return await NotificationService.get_user_unread_notifications(
            db, current_user.user_id, skip, limit
        )
    return await NotificationService.get_user_notifications(
        db, current_user.user_id, skip, limit
    )


@router.get("/stats", response_model=NotificationStatsResponse)
async def get_notification_stats(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Get notification statistics for the current user."""
    return await NotificationService.get_notification_stats(db, current_user.user_id)


@router.post(
    "/", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED
)
async def create_notification(
    notification_data: NotificationCreateRequest,
    db: AsyncSession = get_db_dep,
    current_user: User = get_admin_dep,
):
    """Create a notification as an institution administrator."""
    return await NotificationService.create_notification(db, notification_data)


# Notification Preferences Endpoints (register static routes before dynamic ID routes)


@router.get("/preferences", response_model=NotificationPreferenceResponse)
async def get_notification_preferences(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Get notification preferences for the current user."""
    return await NotificationService.get_notification_preference(
        db, current_user.user_id
    )


@router.put("/preferences", response_model=NotificationPreferenceResponse)
async def update_notification_preferences(
    preference_data: NotificationPreferenceUpdateRequest,
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Update notification preferences for the current user."""
    return await NotificationService.update_notification_preference(
        db, current_user.user_id, preference_data
    )


@router.put("/{notification_id}", response_model=NotificationResponse)
async def update_notification(
    notification_id: int,
    notification_update: NotificationUpdateRequest,
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Update a notification (typically to mark as read)."""
    if notification_update.is_read:
        result = await NotificationService.mark_notification_read(
            db, notification_id, current_user.user_id
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or does not belong to user",
            )
        return result

    # For now, we only support marking as read
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Only marking notifications as read is currently supported",
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Delete a notification."""
    success = await NotificationService.delete_notification(
        db, notification_id, current_user.user_id
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found or does not belong to user",
        )


@router.post("/mark-all-read")
async def mark_all_notifications_read(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
):
    """Mark all notifications as read for the current user."""
    count = await NotificationService.mark_all_notifications_read(
        db, current_user.user_id
    )
    return {"message": f"Marked {count} notifications as read"}
