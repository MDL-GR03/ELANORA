"""Signing in and refreshing a browser session."""

import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.core.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.crud.user import get_user_by_id, get_user_by_username_or_email
from app.model.user import User
from app.schema.common.token import TokenData
from app.service.outbox import enqueue_account_verification_email
from app.service.refresh_session import rotate_refresh_session
from app.service.user_verification import (
    generate_verification_code,
    hash_verification_code,
)
from app.utils.password_hashing import verify_password

logger = get_logger()


@dataclass(frozen=True, slots=True)
class LoginOutcome:
    """A successful sign-in, or one that must first verify the email address."""

    user: User
    needs_verification: bool


@dataclass(frozen=True, slots=True)
class RefreshedTokens:
    """The credentials issued when a session is refreshed."""

    access_token: str
    refresh_token: str
    csrf_token: str


async def authenticate_user(
    db: AsyncSession, login_or_email: str, password: str
) -> User | None:
    """Authenticate user with bcrypt password verification.

    Args:
        db (AsyncSession): Database session.
        login_or_email (str): User username or email.
        password (str): Plain text password.

    Returns:
        User | None: User object if authentication successful, None otherwise.

    """
    user = await get_user_by_username_or_email(db, login_or_email)

    if not user:
        logger.warning("Authentication failed: account not found")
        return None

    if not user.hashed_password:
        logger.warning("Authentication failed: account has no password")
        return None

    # Verify password using bcrypt
    is_valid = verify_password(password, user.hashed_password)

    if is_valid:
        logger.info("User authenticated successfully")
        return user

    logger.warning("Authentication failed: invalid password")
    return None


async def login_user(
    db: AsyncSession,
    login_or_email: str,
    password: str,
) -> LoginOutcome:
    """Sign a researcher in, or refuse with the reason.

    An unverified account receives a fresh verification code instead of a
    session.

    Raises:
        ElanoraError: ``login_invalid`` or ``account_suspended``.

    """
    user = await authenticate_user(db, login_or_email, password)
    if not user:
        raise ElanoraError(ErrorCode.LOGIN_INVALID)

    # A suspended account keeps its data but must never obtain new
    # credentials, even when the presented password is still correct.
    if not user.is_active:
        logger.warning("Login refused: account is suspended")
        raise ElanoraError(ErrorCode.ACCOUNT_SUSPENDED)

    if not user.is_verified_account:
        logger.info("User login requires email verification")
        verification_code = generate_verification_code()
        # Store the hash and encrypted delivery request atomically.
        user.activation_code = hash_verification_code(verification_code)
        # Use the user's instance default language instead of hardcoded 'fr'
        language = user.instance.default_language
        await enqueue_account_verification_email(
            db,
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            code=verification_code,
            language=language,
        )
        await db.commit()
        return LoginOutcome(user=user, needs_verification=True)

    user.last_login = datetime.now(UTC)
    await db.commit()
    logger.info("User logged in successfully")
    return LoginOutcome(user=user, needs_verification=False)


async def refresh_user_tokens(db: AsyncSession, refresh_token: str) -> RefreshedTokens:
    """Rotate a refresh token and issue the next access token.

    Raises:
        ElanoraError: ``session_refresh_failed`` for any token that cannot be
            rotated; the cause is logged, never returned.

    """
    try:
        token_data = verify_refresh_token(refresh_token)
        session_id = uuid.UUID(token_data.session_id or "")
    except Exception as error:
        logger.warning(
            "Token refresh failed; error_type=%s", safe_exception_type(error)
        )
        raise ElanoraError(ErrorCode.SESSION_REFRESH_FAILED) from error

    user = await get_user_by_id(db, int(token_data.sub))
    if not user or not user.is_active:
        logger.warning("Token refresh failed: account inactive or unavailable")
        raise ElanoraError(ErrorCode.SESSION_REFRESH_FAILED)

    new_token_data = TokenData(
        sub=str(user.user_id),
        session_id=str(session_id),
        token_id=secrets.token_hex(16),
    )
    tokens = RefreshedTokens(
        access_token=create_access_token(new_token_data),
        refresh_token=create_refresh_token(new_token_data),
        csrf_token=secrets.token_hex(16),
    )
    if not await rotate_refresh_session(
        db, session_id, refresh_token, tokens.refresh_token
    ):
        await db.rollback()
        raise ElanoraError(ErrorCode.SESSION_REFRESH_FAILED)
    await db.commit()
    logger.info("Tokens refreshed successfully")
    return tokens
