from pydantic import BaseModel, EmailStr, Field, model_validator

from app.core.password_policy import NewPassword, enforce_password_policy
from app.schema.requests.user import AddressRequest


class RegisterWithInvitationRequest(BaseModel):
    invitation_code: str = Field(..., description="Raw invitation code")
    first_name: str
    last_name: str
    username: str
    email: EmailStr
    password: NewPassword
    phone_number: str | None = None
    affiliation: str
    department: str
    address: AddressRequest | None = None

    @model_validator(mode="after")
    def password_is_not_personal(self) -> "RegisterWithInvitationRequest":
        enforce_password_policy(
            self.password,
            (self.username, self.email, self.first_name, self.last_name),
        )
        return self
