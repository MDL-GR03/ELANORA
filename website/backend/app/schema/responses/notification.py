"""Response schemas for notification-related endpoints."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    """Schema for notification response."""

    model_config = ConfigDict(from_attributes=True)

    notification_id: int = Field(
        ..., description="The unique identifier for the notification"
    )
    user_id: int = Field(
        ..., description="The ID of the user receiving the notification"
    )
    title: str = Field(..., description="The title of the notification")
    message: str = Field(..., description="The message content of the notification")
    action_url: str | None = Field(
        None, description="Optional URL for the notification action"
    )
    is_read: bool = Field(..., description="Whether the notification has been read")
    created_at: datetime = Field(..., description="When the notification was created")


class NotificationPreferenceResponse(BaseModel):
    """Schema for notification preference response."""

    model_config = ConfigDict(from_attributes=True)

    preference_id: int = Field(
        ..., description="The unique identifier for the preference"
    )
    user_id: int = Field(..., description="The ID of the user")
    email_enabled: bool = Field(
        ..., description="Whether email notifications are enabled"
    )
    created_at: datetime = Field(..., description="When the preference was created")
    updated_at: datetime = Field(
        ..., description="When the preference was last updated"
    )


class NotificationStatsResponse(BaseModel):
    """Schema for notification statistics response."""

    total_notifications: int = Field(..., description="Total number of notifications")
    unread_notifications: int = Field(..., description="Number of unread notifications")
    read_notifications: int = Field(..., description="Number of read notifications")
