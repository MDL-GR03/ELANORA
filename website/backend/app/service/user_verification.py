"""Verification codes, account verification and password reset."""

import secrets
from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.user import get_user_by_username_or_email
from app.service.refresh_session import revoke_all_refresh_sessions
from app.service.user_passwords import update_password
from app.utils.password_hashing import pwd_context, verify_password

logger = get_logger()


async def verify_account(
    db: AsyncSession, email: str, verification_code: str
) -> dict[str, Any]:
    """Verify user account with activation code.

    Args:
        db (AsyncSession): Database session.
        email (str): User email.
        verification_code (str): Verification code.

    Returns:
        Dict[str, Any]: Verification result.

    """
    logger.info("Account verification attempted")
    user = await get_user_by_username_or_email(db, email)

    if not user:
        logger.warning("Account verification failed: account not found")
        return {"success": False, "message": "User not found"}

    if user.is_verified_account:
        logger.info("Account verification attempted for a verified account")
        return {"success": False, "message": "Account is already verified"}

    # Verify the activation code
    if not verify_password(verification_code, user.activation_code):
        logger.warning("Account verification failed: invalid code")
        return {"success": False, "message": "Invalid verification code"}

    # Mark account as verified
    user.is_verified_account = True
    user.updated_at = datetime.now(UTC)
    await db.commit()

    logger.info("Account verified successfully")
    return {"success": True, "message": "Account verified successfully"}


async def reset_password(
    db: AsyncSession, email: str, reset_code: str, new_password: str
) -> dict[str, Any]:
    """Reset user password with reset code.

    Args:
        db (AsyncSession): Database session.
        email (str): User email.
        reset_code (str): Password reset code.
        new_password (str): New password.

    Returns:
        Dict[str, Any]: Reset result.

    """
    logger.info("Password reset attempted")
    user = await get_user_by_username_or_email(db, email)

    if not user:
        logger.warning("Password reset failed: account not found")
        return {"success": False, "message": "User not found"}

    # Verify reset code
    if not verify_password(reset_code, user.activation_code):
        logger.warning("Password reset failed: invalid code")
        return {"success": False, "message": "Invalid reset code"}

    # Update password
    success = await update_password(db, user, new_password, commit=False)

    if success:
        # Clear activation code after successful reset
        user.activation_code = ""
        user.updated_at = datetime.now(UTC)
        await revoke_all_refresh_sessions(db, user.user_id)
        await db.commit()

    logger.info("Password reset successfully")
    return {"success": True, "message": "Password reset successfully"}


def generate_verification_code() -> str:
    """Generate a 6-digit numeric verification code."""
    return f"{secrets.randbelow(1000000):06d}"


def hash_verification_code(code: str) -> str:
    """Hash verification code."""
    return cast("str", pwd_context.hash(code))
