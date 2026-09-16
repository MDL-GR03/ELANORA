"""Verification codes, account verification and password reset."""

import secrets
from datetime import UTC, datetime
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.errors import ElanoraError, ErrorCode
from app.crud.user import get_user_by_username_or_email
from app.service.refresh_session import revoke_all_refresh_sessions
from app.service.user_passwords import update_password
from app.utils.password_hashing import pwd_context, verify_password

logger = get_logger()


async def verify_account(db: AsyncSession, email: str, verification_code: str) -> None:
    """Mark an account verified when the emailed code matches.

    An unknown address is reported like a wrong code, so the endpoint cannot be
    used to discover which addresses have accounts.

    Raises:
        ElanoraError: ``verification_code_invalid`` or
            ``account_already_verified``.

    """
    logger.info("Account verification attempted")
    user = await get_user_by_username_or_email(db, email)
    if not user:
        logger.warning("Account verification failed: account not found")
        raise ElanoraError(ErrorCode.VERIFICATION_CODE_INVALID)
    if user.is_verified_account:
        logger.info("Account verification attempted for a verified account")
        raise ElanoraError(ErrorCode.ACCOUNT_ALREADY_VERIFIED)
    if not verify_password(verification_code, user.activation_code):
        logger.warning("Account verification failed: invalid code")
        raise ElanoraError(ErrorCode.VERIFICATION_CODE_INVALID)

    user.is_verified_account = True
    user.updated_at = datetime.now(UTC)
    await db.commit()
    logger.info("Account verified successfully")


async def reset_password(
    db: AsyncSession, email: str, reset_code: str, new_password: str
) -> None:
    """Set a new password when the emailed reset code matches.

    Raises:
        ElanoraError: ``verification_code_invalid`` for an unknown address or
            a wrong code, alike; ``password_reset_failed`` if storing fails.

    """
    logger.info("Password reset attempted")
    user = await get_user_by_username_or_email(db, email)
    if not user or not verify_password(reset_code, user.activation_code):
        logger.warning("Password reset failed: invalid code or account")
        raise ElanoraError(ErrorCode.VERIFICATION_CODE_INVALID)

    if not await update_password(db, user, new_password, commit=False):
        raise ElanoraError(ErrorCode.PASSWORD_RESET_FAILED)
    # The code is single-use.
    user.activation_code = ""
    user.updated_at = datetime.now(UTC)
    await revoke_all_refresh_sessions(db, user.user_id)
    await db.commit()
    logger.info("Password reset successfully")


def generate_verification_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_verification_code(code: str) -> str:
    """Hash verification code."""
    return cast("str", pwd_context.hash(code))
