from dataclasses import dataclass


@dataclass
class UserCreateData:
    """Data class for user creation parameters."""

    username: str
    hashed_password: str
    email: str
    first_name: str
    last_name: str
    affiliation: str
    department: str
    activation_code: str
    instance_id: int
    is_verified_account: bool = False
    phone_number: str | None = None
    address_id: int | None = None
