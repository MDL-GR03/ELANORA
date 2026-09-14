from .base import CustomBaseModel


class TokenData(CustomBaseModel):
    """TokenData schema for user authentication.

    Attributes:
        sub (str): The subject identifier for the user (user ID).

    """

    sub: str
    session_id: str | None = None
    token_id: str | None = None
