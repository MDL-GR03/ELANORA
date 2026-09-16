"""Signing in and refreshing a browser session."""

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
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
) -> dict[str, Any]:
    """Handle user login with business logic.

    Returns:
        Dict with success, message, user, needs_verification, email

    """
    # Authenticate user
    user = await authenticate_user(db, login_or_email, password)

    if not user:
        return {"success": False, "message": "Invalid credentials"}

    # A suspended account keeps its data but must never obtain new
    # credentials, even when the presented password is still correct.
    if not user.is_active:
        logger.warning("Login refused: account is suspended")
        return {
            "success": False,
            "message": "This account is suspended. Contact your institution administrator.",
        }

    # Check if email is verified
    if not user.is_verified_account:
        logger.info("User login requires email verification")
        verification_code = generate_verification_code()
        hashed_code = hash_verification_code(verification_code)

        # Store the hash and encrypted delivery request atomically.
        user.activation_code = hashed_code
        await enqueue_account_verification_email(
            db,
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            code=verification_code,
            language="fr",
        )
        await db.commit()

        return {
            "success": True,
            "message": "Login successful but email verification required",
            "needs_verification": True,
            "email": user.email,
            "code_sent": True,
        }
    user.last_login = datetime.now(UTC)
    await db.commit()
    logger.info("User logged in successfully")

    return {"success": True, "message": "Login successful", "user": user}


async def refresh_user_tokens(db: AsyncSession, refresh_token: str) -> dict[str, Any]:
    """Handle token refresh with business logic."""
    try:
        # Verify refresh token
        token_data = verify_refresh_token(refresh_token)
        if token_data.session_id is None:
            return {"success": False, "message": "Token refresh failed"}
        try:
            session_id = uuid.UUID(token_data.session_id)
        except ValueError:
            return {"success": False, "message": "Token refresh failed"}

        # Get user from database
        user = await get_user_by_id(db, int(token_data.sub))

        if not user or not user.is_active:
            logger.warning("Token refresh failed: account inactive or unavailable")
            return {
                "success": False,
                "message": "User account is inactive or not found",
            }

        # Create new tokens
        new_token_data = TokenData(
            sub=str(user.user_id),
            session_id=str(session_id),
            token_id=secrets.token_hex(16),
        )
        new_access_token = create_access_token(new_token_data)
        new_refresh_token = create_refresh_token(new_token_data)
        csrf_token = secrets.token_hex(16)

        if not await rotate_refresh_session(
            db, session_id, refresh_token, new_refresh_token
        ):
            await db.rollback()
            return {"success": False, "message": "Token refresh failed"}
        await db.commit()

        logger.info("Tokens refreshed successfully")
        return {
            "success": True,
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "csrf_token": csrf_token,
            "message": "Tokens refreshed successfully",
        }

    except Exception as e:
        logger.error("Token refresh failed; error_type=%s", safe_exception_type(e))
        return {"success": False, "message": "Token refresh failed"}
