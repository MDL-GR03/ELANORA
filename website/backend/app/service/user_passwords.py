"""Hashing and changing passwords."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.user import update_user_password
from app.model.user import User
from app.service.refresh_session import revoke_all_refresh_sessions
from app.utils.password_hashing import hash_password, verify_password

logger = get_logger()


async def update_password(
    db: AsyncSession,
    user: User,
    new_password: str,
    *,
    commit: bool = True,
) -> bool:
    """Update user's password with bcrypt hashing.

    Args:
        db (AsyncSession): Database session.
        user (User): User object to update.
        new_password (str): New plain text password.

    Returns:
        bool: True if update successful, False otherwise.

    """
    logger.info("Updating an account password")
    new_password_hash = hash_password(new_password)
    success = await update_user_password(db, user, new_password_hash)

    if success:
        user.updated_at = datetime.now(UTC)
        if commit:
            await revoke_all_refresh_sessions(db, user.user_id)
            await db.commit()
        logger.info("Account password updated successfully")
    else:
        logger.error("Failed to update account password")

    return success


async def verify_current_password(user: User, current_password: str) -> bool:
    """Verify user's current password.

    Args:
        user (User): User object.
        current_password (str): Current plain text password.

    Returns:
        bool: True if current password is correct.

    """
    if not user.hashed_password:
        logger.warning("Password verification failed: account has no password")
        return False

    result = verify_password(current_password, user.hashed_password)
    if result:
        logger.debug("Current password verified")
    else:
        logger.warning("Current password verification failed")

    return result


async def change_password(
    db: AsyncSession, user: User, current_password: str, new_password: str
) -> dict[str, Any]:
    """Change user password with current password verification.

    Args:
        db (AsyncSession): Database session.
        user (User): Current user.
        current_password (str): Current password.
        new_password (str): New password.

    Returns:
        Dict[str, Any]: Change result.

    """
    logger.info("Password change attempted")

    # Verify current password
    if not verify_password(current_password, user.hashed_password):
        logger.warning("Password change failed: incorrect current password")
        return {"success": False, "message": "Current password is incorrect"}

    # Update password
    success = await update_password(db, user, new_password, commit=False)

    if success:
        user.updated_at = datetime.now(UTC)
        await revoke_all_refresh_sessions(db, user.user_id)
        await db.commit()

        logger.info("Password changed successfully")
        return {"success": True, "message": "Password changed successfully"}

    logger.error("Password change failed during update")
    return {"success": False, "message": "Failed to change password"}
