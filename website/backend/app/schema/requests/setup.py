from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, EmailStr, StringConstraints, model_validator

from app.core.password_policy import NewPassword, enforce_password_policy

HexColor = Annotated[str, StringConstraints(pattern=r"^#[0-9A-Fa-f]{6}$")]
TrimmedText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class SetupInitializeRequest(BaseModel):
    """All information required for a one-time institutional bootstrap."""

    instance_name: Annotated[TrimmedText, StringConstraints(max_length=100)]
    institution_name: Annotated[TrimmedText, StringConstraints(max_length=100)]
    contact_email: EmailStr
    domain: Annotated[TrimmedText, StringConstraints(max_length=100)]
    timezone: Annotated[TrimmedText, StringConstraints(max_length=50)] = "UTC"
    default_language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")] = "en"
    primary_color: HexColor = "#2563eb"
    secondary_color: HexColor = "#0f766e"
    accent_color: HexColor = "#d97706"
    admin_username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=3, max_length=50)
    ]
    admin_email: EmailStr
    admin_first_name: Annotated[TrimmedText, StringConstraints(max_length=50)]
    admin_last_name: Annotated[TrimmedText, StringConstraints(max_length=50)]
    admin_affiliation: Annotated[TrimmedText, StringConstraints(max_length=100)]
    admin_department: Annotated[TrimmedText, StringConstraints(max_length=100)]
    password: NewPassword
    password_confirmation: str

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupInitializeRequest":
        if self.password != self.password_confirmation:
            raise ValueError("administrator password confirmation does not match")
        enforce_password_policy(
            self.password,
            (
                self.admin_username,
                self.admin_email,
                self.admin_first_name,
                self.admin_last_name,
                self.institution_name,
                self.instance_name,
            ),
        )
        return self


class InstanceBrandingUpdateRequest(BaseModel):
    """Owner-editable visual identity for this installation."""

    instance_name: Annotated[TrimmedText, StringConstraints(max_length=100)] | None = (
        None
    )
    institution_name: (
        Annotated[TrimmedText, StringConstraints(max_length=100)] | None
    ) = None
    contact_email: EmailStr | None = None
    primary_color: HexColor | None = None
    secondary_color: HexColor | None = None
    accent_color: HexColor | None = None


class InstanceSettingsUpdateRequest(BaseModel):
    """Administrator-editable general settings for this installation.
    
    These settings control the database and system-level configuration.
    """

    domain: Annotated[TrimmedText, StringConstraints(max_length=100)] | None = None
    timezone: Annotated[TrimmedText, StringConstraints(max_length=50)] | None = None
    default_language: Annotated[str, StringConstraints(pattern=r"^[a-z]{2,3}$")] | None = None
    max_file_size_mb: Decimal | None = None
    max_users: int | None = None
    is_active: bool | None = None
