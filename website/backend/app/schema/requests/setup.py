from typing import Annotated

from pydantic import BaseModel, EmailStr, Field, StringConstraints, model_validator

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
    password: str = Field(min_length=12, max_length=256)
    password_confirmation: str = Field(min_length=12, max_length=256)

    @model_validator(mode="after")
    def passwords_match(self) -> "SetupInitializeRequest":
        if self.password != self.password_confirmation:
            raise ValueError("administrator password confirmation does not match")
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
