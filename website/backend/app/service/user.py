"""User service layer - Business logic and password management."""

import secrets
import uuid
from datetime import UTC, datetime
from typing import Any, cast

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.crud.user import (
    check_user_exists_by_email,
    check_user_exists_by_username,
    create_user_in_db,
    get_user_by_id,
    get_user_by_username_or_email,
    update_user_password,
    update_user_profile,
)
from app.model.user import User
from app.schema.common.token import TokenData
from app.schema.common.user import UserCreateData
from app.schema.requests.user import (
    AddressRequest,
    ProfileUpdateRequest,
)
from app.service.address import AddressService
from app.service.notification import NotificationService
from app.service.outbox import enqueue_account_verification_email
from app.service.refresh_session import (
    revoke_all_refresh_sessions,
    rotate_refresh_session,
)
from app.utils.database import DatabaseUtils

# Get logger for this module
logger = get_logger()

# Create a passlib context for bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    """Service for user-related business logic."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt.

        Args:
            password (str): The plaintext password to be hashed.

        Returns:
            str: The hashed password.

        """
        return str(pwd_context.hash(password))

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against a bcrypt hash.

        Args:
            plain_password (str): The plain text password.
            hashed_password (str): The hashed password.

        Returns:
            bool: True if password matches.

        """
        return bool(pwd_context.verify(plain_password, hashed_password))

    @classmethod
    async def authenticate_user(
        cls, db: AsyncSession, login_or_email: str, password: str
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
        is_valid = cls.verify_password(password, user.hashed_password)

        if is_valid:
            logger.info("User authenticated successfully")
            return user

        logger.warning("Authentication failed: invalid password")
        return None

    @classmethod
    async def login_user(
        cls,
        db: AsyncSession,
        login_or_email: str,
        password: str,
    ) -> dict[str, Any]:
        """Handle user login with business logic.

        Returns:
            Dict with success, message, user, needs_verification, email

        """
        # Authenticate user
        user = await cls.authenticate_user(db, login_or_email, password)

        if not user:
            return {"success": False, "message": "Invalid credentials"}

        # Check if email is verified
        if not user.is_verified_account:
            logger.info("User login requires email verification")
            verification_code = cls._generate_verification_code()
            hashed_code = cls._hash_verification_code(verification_code)

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

    @classmethod
    async def refresh_user_tokens(
        cls, db: AsyncSession, refresh_token: str
    ) -> dict[str, Any]:
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

    @classmethod
    async def create_user(
        cls,
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
            hashed_password = cls.hash_password(password)

            # Determine activation code logic
            activation_code = ""
            if not is_verified:
                # If email is not verified, generate activation code
                activation_code = cls._generate_verification_code()
                activation_code = cls._hash_verification_code(activation_code)

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

    @classmethod
    async def update_password(
        cls,
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
        new_password_hash = cls.hash_password(new_password)
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

    @classmethod
    async def verify_current_password(cls, user: User, current_password: str) -> bool:
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

        result = cls.verify_password(current_password, user.hashed_password)
        if result:
            logger.debug("Current password verified")
        else:
            logger.warning("Current password verification failed")

        return result

    @classmethod
    async def update_user_profile(
        cls,
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
                username_available = await cls.check_username_availability_for_update(
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

    @classmethod
    async def check_username_availability(cls, db: AsyncSession, username: str) -> bool:
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

    @classmethod
    async def check_username_availability_for_update(
        cls, db: AsyncSession, username: str, exclude_user_id: int
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

    @classmethod
    async def check_email_availability(cls, db: AsyncSession, email: str) -> bool:
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

    @classmethod
    async def verify_account(
        cls, db: AsyncSession, email: str, verification_code: str
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
        if not cls.verify_password(verification_code, user.activation_code):
            logger.warning("Account verification failed: invalid code")
            return {"success": False, "message": "Invalid verification code"}

        # Mark account as verified
        user.is_verified_account = True
        user.updated_at = datetime.now(UTC)
        await db.commit()

        logger.info("Account verified successfully")
        return {"success": True, "message": "Account verified successfully"}

    @classmethod
    async def reset_password(
        cls, db: AsyncSession, email: str, reset_code: str, new_password: str
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
        if not cls.verify_password(reset_code, user.activation_code):
            logger.warning("Password reset failed: invalid code")
            return {"success": False, "message": "Invalid reset code"}

        # Update password
        success = await cls.update_password(db, user, new_password, commit=False)

        if success:
            # Clear activation code after successful reset
            user.activation_code = ""
            user.updated_at = datetime.now(UTC)
            await revoke_all_refresh_sessions(db, user.user_id)
            await db.commit()

        logger.info("Password reset successfully")
        return {"success": True, "message": "Password reset successfully"}

    @classmethod
    async def change_password(
        cls, db: AsyncSession, user: User, current_password: str, new_password: str
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
        if not cls.verify_password(current_password, user.hashed_password):
            logger.warning("Password change failed: incorrect current password")
            return {"success": False, "message": "Current password is incorrect"}

        # Update password
        success = await cls.update_password(db, user, new_password, commit=False)

        if success:
            user.updated_at = datetime.now(UTC)
            await revoke_all_refresh_sessions(db, user.user_id)
            await db.commit()

            logger.info("Password changed successfully")
            return {"success": True, "message": "Password changed successfully"}

        logger.error("Password change failed during update")
        return {"success": False, "message": "Failed to change password"}

    @classmethod
    async def get_user_by_email(cls, db: AsyncSession, email: str) -> User | None:
        """Get a user by email address."""
        return await get_user_by_username_or_email(db, email)

    # Private helper methods for business logic
    @staticmethod
    def _generate_verification_code() -> str:
        """Generate a 6-digit numeric verification code."""
        return f"{secrets.randbelow(1000000):06d}"

    @staticmethod
    def _hash_verification_code(code: str) -> str:
        """Hash verification code."""
        return cast("str", pwd_context.hash(code))
