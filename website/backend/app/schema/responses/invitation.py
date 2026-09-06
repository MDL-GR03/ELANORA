"""Response schemas for invitation operations."""

from datetime import datetime

from app.model.enums import InvitationStatus, ProjectPermission
from app.schema.common.base import CustomBaseModel


class InvitationResponse(CustomBaseModel):
    """Schema for invitation data."""

    invitation_id: int
    receiver_email: str
    project_id: int
    project_permission: ProjectPermission
    status: InvitationStatus
    created_at: datetime
    expires_at: datetime
    responded_at: datetime | None = None
    sender_username: str | None = None
    project_name: str | None = None


class InvitationSendResponse(CustomBaseModel):
    """Schema for invitation send response."""

    success: bool
    message: str
    invitation_id: int | None = None
    invitation_code: str | None = None


class InvitationListResponse(CustomBaseModel):
    """Schema for invitation list response."""

    invitations: list[InvitationResponse]
    total: int


class InvitationValidationResponse(CustomBaseModel):
    """Schema for invitation validation response."""

    valid: bool
    invitation: InvitationResponse | None = None
    message: str
    user_exists: bool = False
