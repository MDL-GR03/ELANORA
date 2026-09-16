from pydantic import BaseModel, EmailStr, Field

from app.core.password_policy import NewPassword
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
