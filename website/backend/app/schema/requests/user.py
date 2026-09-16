from pydantic import EmailStr, Field

from app.core.password_policy import NewPassword
from app.schema.common.base import CustomBaseModel


class AddressRequest(CustomBaseModel):
    """Schema for address information."""

    street_number: str | None = None
    street_name: str
    city_name: str
    country_code: str
    country_name: str
    postal_code: str
    address_line_2: str | None = None


class LoginRequest(CustomBaseModel):
    """LoginRequest schema for user login."""

    login: str
    password: str


class ProfileUpdateRequest(CustomBaseModel):
    """Schema for updating user profile information."""

    username: str | None = None
    email: EmailStr | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone_number: str | None = None
    affiliation: str | None = None
    department: str | None = None
    address: AddressRequest | None = None


class ForgotPasswordRequest(CustomBaseModel):
    """Schema for requesting a password reset email."""

    email: EmailStr
    language: str = "en"


class ResetPasswordRequest(CustomBaseModel):
    """Schema for resetting a user's password."""

    email: str
    code: str
    new_password: NewPassword


class SendVerificationEmailRequest(CustomBaseModel):
    """Schema for sending email verification code."""

    email: EmailStr
    language: str = "en"


class VerifyEmailRequest(CustomBaseModel):
    """Schema for verifying email with code."""

    email: EmailStr
    code: str


class ChangePasswordRequest(CustomBaseModel):
    """Schema for changing user password."""

    current_password: str
    new_password: NewPassword


class AccountStatusRequest(CustomBaseModel):
    """Administrator request to suspend or restore an institution account."""

    is_active: bool
    reason: str = Field(min_length=3, max_length=500)
