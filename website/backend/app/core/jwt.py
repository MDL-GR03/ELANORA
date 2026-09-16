from datetime import UTC, datetime, timedelta

import jwt
from jwt.exceptions import ExpiredSignatureError, PyJWTError

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    JWT_ALGORITHM,
    JWT_SECRET_KEY,
    REFRESH_TOKEN_EXPIRE_DAYS,
)
from app.core.errors import ElanoraError, ErrorCode
from app.schema.common.token import TokenData

# Token type constants for clarity and to avoid hardcoded string warnings
ACCESS_TOKEN_TYPE = "access"  # noqa: S105
REFRESH_TOKEN_TYPE = "refresh"  # noqa: S105


def create_token(
    data: TokenData,
    token_type: str = ACCESS_TOKEN_TYPE,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT token with the specified data and type.

    Args:
        data: The data to encode in the token
        token_type: The type of token to create ("access" or "refresh")
        expires_delta: Optional custom expiration time

    Returns:
        str: The encoded JWT token

    """
    # Set expiration time based on token type or custom expiration
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    elif token_type == ACCESS_TOKEN_TYPE:
        expire = datetime.now(UTC) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    elif token_type == REFRESH_TOKEN_TYPE:
        expire = datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        raise ValueError("Invalid token_type specified.")

    to_encode = data.model_dump() if hasattr(data, "model_dump") else dict(data)
    to_encode["exp"] = expire
    to_encode["token_type"] = token_type

    if not JWT_SECRET_KEY:
        raise ValueError("JWT_SECRET_KEY is not set in the environment variables.")

    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return str(encoded_jwt)


def verify_token(token: str, expected_token_type: str = ACCESS_TOKEN_TYPE) -> TokenData:
    """Verify a JWT token and extract the user data.

    Args:
        token: The JWT token to verify
        expected_token_type: Optional token type to verify ("access" or "refresh")

    Returns:
        TokenData: The user data extracted from the token

    Raises:
        ElanoraError: If the token is invalid or expired

    """
    try:
        if not JWT_SECRET_KEY:
            raise ValueError("JWT_SECRET_KEY is not set in the environment variables.")

        payload = jwt.decode(
            token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM], leeway=10
        )
        sub = payload.get("sub")
        token_type = payload.get("token_type")

        # Check token fields exist
        if sub is None:
            raise ElanoraError(ErrorCode.TOKEN_INVALID)

        # If token type verification is requested
        if token_type != expected_token_type:
            raise ElanoraError(ErrorCode.TOKEN_INVALID)
        return TokenData(
            sub=sub,
            session_id=payload.get("session_id"),
            token_id=payload.get("token_id"),
        )

    except ExpiredSignatureError as err:
        raise ElanoraError(ErrorCode.TOKEN_EXPIRED) from err

    except PyJWTError as err:
        raise ElanoraError(ErrorCode.CREDENTIALS_INVALID) from err


def create_access_token(data: TokenData, expires_delta: timedelta | None = None) -> str:
    """Create a short-lived access token for API access."""
    return create_token(data, token_type=ACCESS_TOKEN_TYPE, expires_delta=expires_delta)


def create_refresh_token(
    data: TokenData, expires_delta: timedelta | None = None
) -> str:
    """Create a long-lived refresh token."""
    return create_token(
        data, token_type=REFRESH_TOKEN_TYPE, expires_delta=expires_delta
    )


def verify_access_token(token: str) -> TokenData:
    """Verify an access token and extract user data."""
    return verify_token(token, expected_token_type=ACCESS_TOKEN_TYPE)


def verify_refresh_token(token: str) -> TokenData:
    """Verify a refresh token and extract user data."""
    return verify_token(token, expected_token_type=REFRESH_TOKEN_TYPE)
