"""Creating accounts and checking that a name or address is free."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.user import (
    check_user_exists_by_email,
    check_user_exists_by_username,
    create_user_in_db,
    get_user_by_username_or_email,
)
from app.model.user import User
from app.schema.common.user import UserCreateData
from app.schema.requests.user import AddressRequest
from app.service.address import AddressService
from app.service.notification import NotificationService
from app.service.user_verification import (
    generate_verification_code,
    hash_verification_code,
)
from app.utils.database import DatabaseUtils
from app.utils.password_hashing import hash_password

logger = get_logger()


async def create_user(  # noqa: PLR0913, PLR0917 - the account's own fields
    db: AsyncSession,
    username: str,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    affiliation: str,
    department: str,
    instance_id: int,
    is_verified: bool = False,
    phone_number: str | None = None,
    address_data: AddressRequest | None = None,
    *,
    commit: bool = True,
) -> User:
    """Create a new user with bcrypt password hashing."""
    try:
        logger.info("Creating a user account")

        # Hash the password
        hashed_password = hash_password(password)

        # Determine activation code logic
        activation_code = ""
        if not is_verified:
            # If email is not verified, generate activation code
            activation_code = generate_verification_code()
            activation_code = hash_verification_code(activation_code)

        # Create address if provided
        address_id = None
        if address_data:
            address = await AddressService.create_address(
                db, address_data, commit=False
            )
            address_id = address.address_id

        # Create UserCreateData object
        user_data = UserCreateData(
            username=username,
            hashed_password=hashed_password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            affiliation=affiliation,
            department=department,
            activation_code=activation_code,
            instance_id=instance_id,
            is_verified_account=is_verified,
            address_id=address_id,
        )

        # Create user in database
        user = await create_user_in_db(db, user_data)

        # Flush to get the user_id before creating preferences
        await db.flush()

        # Create default notification preferences
        await NotificationService.create_user_preference(
            db, user.user_id, email_enabled=True
        )

        if commit:
            await db.commit()
        logger.info("User account created successfully")
        return user
    except Exception:
        await db.rollback()
        raise


async def check_username_availability(db: AsyncSession, username: str) -> bool:
    """Check if a username is available for registration.

    Args:
        db (AsyncSession): Database session.
        username (str): Username to check.

    Returns:
        bool: True if available, False if taken.

    """
    is_available = not await check_user_exists_by_username(db, username)
    logger.debug(
        f"Username availability check for '{username}': {'available' if is_available else 'taken'}"
    )
    return is_available


async def check_username_availability_for_update(
    db: AsyncSession, username: str, exclude_user_id: int
) -> bool:
    """Check if a username is available for profile update (excluding current user).

    Args:
        db (AsyncSession): Database session.
        username (str): Username to check.
        exclude_user_id (int): User ID to exclude from check.

    Returns:
        bool: True if available, False if taken by another user.

    """
    # Get user with this username (if any)
    existing_user = await DatabaseUtils.get_one_by_filter(
        db, User, {"username": username}
    )

    # If no user exists with this username, it's available
    if not existing_user:
        return True

    # If the user with this username is the current user, it's available
    return existing_user.user_id == exclude_user_id


async def check_email_availability(db: AsyncSession, email: str) -> bool:
    """Check if an email is available for registration.

    Args:
        db (AsyncSession): Database session.
        email (str): Email to check.

    Returns:
        bool: True if available, False if taken.

    """
    is_available = not await check_user_exists_by_email(db, email)
    logger.debug(
        f"Email availability check for '{email}': {'available' if is_available else 'taken'}"
    )
    return is_available


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email address."""
    return await get_user_by_username_or_email(db, email)


# Private helper methods for business logic
