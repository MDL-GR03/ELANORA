"""Updating a researcher's own profile."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.errors import ElanoraError, ErrorCode
from app.crud.user import update_user_profile
from app.model.user import User
from app.schema.requests.user import ProfileUpdateRequest
from app.service.user_registration import check_username_availability_for_update

logger = get_logger()


async def update_profile(
    db: AsyncSession,
    user: User,
    profile_data: ProfileUpdateRequest,
) -> list[str]:
    """Update the fields a researcher sent, returning their names.

    Raises:
        ElanoraError: ``username_taken`` or ``profile_no_changes``.

    """
    logger.info("Updating an account profile")
    if profile_data.username is not None and not (
        await check_username_availability_for_update(
            db, profile_data.username, user.user_id
        )
    ):
        logger.warning("Username already taken during profile update")
        raise ElanoraError(ErrorCode.USERNAME_TAKEN)

    update_fields: dict[str, object] = {
        name: value
        for name, value in profile_data.model_dump(
            include={
                "username",
                "email",
                "first_name",
                "last_name",
                "phone_number",
                "affiliation",
                "department",
            }
        ).items()
        if value is not None
    }
    if not update_fields:
        logger.warning("Profile update attempted with no fields to update")
        raise ElanoraError(ErrorCode.PROFILE_NO_CHANGES)

    updated_field_names = list(update_fields)
    update_fields["updated_at"] = datetime.now(UTC)
    try:
        if not await update_user_profile(db, user, **update_fields):
            raise ElanoraError(ErrorCode.PROFILE_UPDATE_FAILED)
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    logger.info("Account profile updated successfully; fields=%s", updated_field_names)
    return updated_field_names
