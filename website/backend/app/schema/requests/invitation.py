"""Request schemas for invitation operations."""

from pydantic import EmailStr, Field, field_validator

from app.model.enums import ProjectPermission
from app.schema.common.base import CustomBaseModel


class InvitationSendRequest(CustomBaseModel):
    """Schema for sending an invitation by email."""

    receiver_email: EmailStr
    project_name: str
    project_permission: ProjectPermission = ProjectPermission.READ
    expires_in_days: int = Field(default=7, ge=1, le=30)
    language: str = "en"
    message: str | None = None

    @field_validator("receiver_email")
    @classmethod
    def normalize_receiver_email(cls, value: EmailStr) -> str:
        """Use one canonical representation for membership and duplicate checks."""
        return str(value).strip().lower()

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        """Accept only languages for which invitation templates exist."""
        normalized = value.strip().lower()
        if normalized not in {"en", "fr"}:
            raise ValueError("Invitation language must be 'en' or 'fr'")
        return normalized


class InvitationAcceptRequest(CustomBaseModel):
    """Schema for accepting an invitation during registration."""

    invitation_id: int
