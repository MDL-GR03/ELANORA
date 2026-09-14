from pydantic import EmailStr, Field, field_validator

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


class RegistrationRequest(CustomBaseModel):
    """RegistrationRequest schema for user registration."""

    username: str
    password: str
    confirm_password: str
    first_name: str
    last_name: str
    email: EmailStr
    confirm_email: EmailStr
    phone_number: str | None = None
    affiliation: str
    department: str
    address: AddressRequest | None = None

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, values):
        """Ensure that the confirmed password matches the original password."""
        if "password" in values.data and v != values.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    @field_validator("confirm_email")
    @classmethod
    def emails_match(cls, v, values):
        """Ensure that the confirmed email matches the original email."""
        if "email" in values.data and v != values.data["email"]:
            raise ValueError("Emails do not match")
        return v


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


class PasswordUpdateRequest(CustomBaseModel):
    """Schema for updating user password."""

    current_password: str
    new_password: str


class ForgotPasswordRequest(CustomBaseModel):
    """Schema for requesting a password reset email."""

    email: EmailStr
    language: str = "en"


class ContactForm(CustomBaseModel):
    """Schema for contact form submission."""

    email: EmailStr
    category: str
    subject: str
    message: str


class ResetPasswordRequest(CustomBaseModel):
    """Schema for resetting a user's password."""

    email: str
    code: str
    new_password: str


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
    new_password: str


class AccountStatusRequest(CustomBaseModel):
    """Administrator request to suspend or restore an institution account."""

    is_active: bool
    reason: str = Field(min_length=3, max_length=500)
