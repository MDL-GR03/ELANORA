"""User CRUD operations - Pure database access layer."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User, UserRole
from app.schema.common.user import UserCreateData
from app.utils.database import DatabaseUtils

ROLE_ADMIN = UserRole.ADMIN


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    """Retrieve a user by their ID with relationships pre-loaded."""
    # Use DatabaseUtils for basic get_by_id
    return await DatabaseUtils.get_by_id(db, User, "user_id", user_id)


async def get_user_by_username_or_email(
    db: AsyncSession, login_or_email: str
) -> User | None:
    """Retrieve a user by their username or email."""
    filters = {"username": login_or_email}
    user = await DatabaseUtils.get_one_by_filter(db, User, filters)
    if user:
        return user
    filters = {"email": login_or_email}
    return await DatabaseUtils.get_one_by_filter(db, User, filters)


async def create_user_in_db(
    db: AsyncSession,
    user_data: UserCreateData,
    **additional_fields,
) -> User:
    """Create a new user in the database."""
    user = User(
        username=user_data.username,
        hashed_password=user_data.hashed_password,
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone_number=user_data.phone_number,
        affiliation=user_data.affiliation,
        department=user_data.department,
        activation_code=user_data.activation_code,
        instance_id=user_data.instance_id,
        address_id=user_data.address_id,
        is_verified_account=user_data.is_verified_account,
        role=UserRole.PUBLIC,
        is_active=True,
        **additional_fields,
    )
    # Use DatabaseUtils for create and commit
    return await DatabaseUtils.create(db, user)


async def update_user_password(
    db: AsyncSession, user: User, new_password_hash: str
) -> bool:
    """Update user's password hash in database."""
    filters = {"user_id": user.user_id}
    update_fields = {"hashed_password": new_password_hash}
    try:
        await DatabaseUtils.update_by_filter(db, User, filters, update_fields)
        return True
    except Exception:
        await db.rollback()
        return False


async def update_user_profile(db: AsyncSession, user: User, **update_fields) -> bool:
    """Update user profile fields in database."""
    filters = {"user_id": user.user_id}
    try:
        await DatabaseUtils.update_by_filter(db, User, filters, update_fields)
        return True
    except Exception:
        await db.rollback()
        return False


async def validate_user_exists_and_active(db: AsyncSession, user_id: int) -> bool:
    """Validate that a user exists and has an active account."""
    filters = {"user_id": user_id, "is_active": True}
    user = await DatabaseUtils.get_one_by_filter(db, User, filters)
    return user is not None


async def get_admin_emails(db: AsyncSession) -> list[str]:
    """Get email addresses of all site administrators."""
    filters = {"role": ROLE_ADMIN, "is_active": True}
    admins = await DatabaseUtils.get_by_filter(db, User, filters)
    admin_emails = [admin.email for admin in admins]
    if not admin_emails:
        return ["admin@example.com"]
    return admin_emails


async def check_user_exists_by_username(db: AsyncSession, username: str) -> bool:
    """Check if a user with the given username exists."""
    # Use DatabaseUtils.exists
    return await DatabaseUtils.exists(db, User, "username", username)


async def check_user_exists_by_email(db: AsyncSession, email: str) -> bool:
    """Check if a user with the given email exists."""
    # Use DatabaseUtils.exists
    return await DatabaseUtils.exists(db, User, "email", email)


async def get_all_active_users(db: AsyncSession, instance_id: int) -> list[User]:
    """Get active users belonging to one institution installation."""
    filters = {"is_active": True, "instance_id": instance_id}
    return await DatabaseUtils.get_by_filter(db, User, filters)
