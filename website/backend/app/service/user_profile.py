"""Updating a researcher's own profile."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.user import update_user_profile
from app.model.user import User
from app.schema.requests.user import ProfileUpdateRequest
from app.service.user_registration import check_username_availability_for_update

logger = get_logger()


async def update_profile(
    db: AsyncSession,
    user: User,
    profile_data: ProfileUpdateRequest,
) -> dict[str, Any]:
    """Update user profile with validation."""
    try:
        logger.info("Updating an account profile")

        # Prepare update fields
        update_fields: dict[str, Any] = {}
        updated_field_names: list[str] = []

        field_mapping = {
            "username": profile_data.username,
            "email": profile_data.email,
            "first_name": profile_data.first_name,
            "last_name": profile_data.last_name,
            "phone_number": profile_data.phone_number,
            "affiliation": profile_data.affiliation,
            "department": profile_data.department,
        }

        # Special validation for username if provided
        if profile_data.username is not None:
            # Check if username is already taken by another user (exclude current user)
            username_available = await check_username_availability_for_update(
                db, profile_data.username, user.user_id
            )
            if not username_available:
                logger.warning("Username already taken during profile update")
                return {
                    "success": False,
                    "message": "Username already taken",
                    "updated_fields": [],
                }

        for field_name, field_value in field_mapping.items():
            if field_value is not None:
                update_fields[field_name] = field_value
                updated_field_names.append(field_name)

        if not update_fields:
            logger.warning("Profile update attempted with no fields to update")
            return {
                "success": False,
                "message": "No fields to update",
                "updated_fields": [],
            }

        update_fields["updated_at"] = datetime.now(UTC)

        # Update in database
        success = await update_user_profile(db, user, **update_fields)

        if success:
            await db.commit()
            logger.info(
                "Account profile updated successfully; fields=%s",
                updated_field_names,
            )
        else:
            await db.rollback()
            logger.error("Account profile update failed")

        return {
            "success": success,
            "message": "Profile updated successfully"
            if success
            else "Profile update failed",
            "updated_fields": updated_field_names if success else [],
        }
    except Exception:
        await db.rollback()
        raise
