"""User use cases: credentials, sessions, registration, profile and status.

The work lives in focused modules; ``UserService`` remains the entry point its
callers already use, and the account-status errors are still importable here.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.user import User
from app.schema.requests.user import AddressRequest, ProfileUpdateRequest
from app.service import (
    user_account_status,
    user_passwords,
    user_profile,
    user_registration,
    user_sessions,
    user_verification,
)
from app.service.user_errors import (
    AccountNotFoundError,
    AccountStatusConflictError,
    AdministratorNoLongerActiveError,
    LastAdministratorError,
    RedundantAccountStatusError,
    SelfAccountStatusError,
)
from app.utils.password_hashing import hash_password, pwd_context, verify_password

__all__ = [
    "AccountNotFoundError",
    "AccountStatusConflictError",
    "AdministratorNoLongerActiveError",
    "LastAdministratorError",
    "RedundantAccountStatusError",
    "SelfAccountStatusError",
    "UserService",
    "pwd_context",
]


class UserService:
    """Entry point for account credentials, sessions, profiles and status."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password with bcrypt."""
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Whether a plain password matches a stored bcrypt hash."""
        return verify_password(plain_password, hashed_password)

    @classmethod
    async def authenticate_user(
        cls, db: AsyncSession, login_or_email: str, password: str
    ) -> User | None:
        """Authenticate a researcher by username or email address."""
        return await user_sessions.authenticate_user(db, login_or_email, password)

    @classmethod
    async def login_user(
        cls, db: AsyncSession, login_or_email: str, password: str
    ) -> dict[str, Any]:
        """Sign a researcher in, reporting why when it is refused."""
        return await user_sessions.login_user(db, login_or_email, password)

    @classmethod
    async def refresh_user_tokens(
        cls, db: AsyncSession, refresh_token: str
    ) -> dict[str, Any]:
        """Rotate a refresh token and issue the next access token."""
        return await user_sessions.refresh_user_tokens(db, refresh_token)

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
        return await user_registration.create_user(
            db,
            username,
            email,
            password,
            first_name,
            last_name,
            affiliation,
            department,
            instance_id,
            is_verified,
            phone_number,
            address_data,
            commit=commit,
        )

    @classmethod
    async def check_username_availability(cls, db: AsyncSession, username: str) -> bool:
        """Whether a username is free."""
        return await user_registration.check_username_availability(db, username)

    @classmethod
    async def check_username_availability_for_update(
        cls, db: AsyncSession, username: str, exclude_user_id: int
    ) -> bool:
        """Whether a username is free for this account to take."""
        return await user_registration.check_username_availability_for_update(
            db, username, exclude_user_id
        )

    @classmethod
    async def check_email_availability(cls, db: AsyncSession, email: str) -> bool:
        """Whether an email address is free."""
        return await user_registration.check_email_availability(db, email)

    @classmethod
    async def get_user_by_email(cls, db: AsyncSession, email: str) -> User | None:
        """The account with this email address, if any."""
        return await user_registration.get_user_by_email(db, email)

    @classmethod
    async def update_password(
        cls, db: AsyncSession, user: User, new_password: str, *, commit: bool = True
    ) -> bool:
        """Replace an account's password."""
        return await user_passwords.update_password(
            db, user, new_password, commit=commit
        )

    @classmethod
    async def verify_current_password(cls, user: User, current_password: str) -> bool:
        """Whether the given password is the account's current one."""
        return await user_passwords.verify_current_password(user, current_password)

    @classmethod
    async def change_password(
        cls, db: AsyncSession, user: User, current_password: str, new_password: str
    ) -> dict[str, Any]:
        """Change a password after checking the current one."""
        return await user_passwords.change_password(
            db, user, current_password, new_password
        )

    @classmethod
    async def verify_account(
        cls, db: AsyncSession, email: str, verification_code: str
    ) -> dict[str, Any]:
        """Verify an account with its activation code."""
        return await user_verification.verify_account(db, email, verification_code)

    @classmethod
    async def reset_password(
        cls, db: AsyncSession, email: str, reset_code: str, new_password: str
    ) -> dict[str, Any]:
        """Reset a password with a valid reset code."""
        return await user_verification.reset_password(
            db, email, reset_code, new_password
        )

    @classmethod
    async def update_user_profile(
        cls,
        db: AsyncSession,
        user: User,
        profile_data: ProfileUpdateRequest,
    ) -> dict[str, Any]:
        """Update a researcher's own profile."""
        return await user_profile.update_profile(db, user, profile_data)

    @classmethod
    async def set_account_active(
        cls,
        db: AsyncSession,
        *,
        actor: User,
        target_user_id: int,
        is_active: bool,
        reason: str,
    ) -> User:
        """Suspend or restore an institution account with safety invariants."""
        return await user_account_status.set_account_active(
            db,
            actor=actor,
            target_user_id=target_user_id,
            is_active=is_active,
            reason=reason,
        )

    @staticmethod
    def _generate_verification_code() -> str:
        """A fresh verification code."""
        return user_verification.generate_verification_code()

    @staticmethod
    def _hash_verification_code(code: str) -> str:
        """Hash a verification code the way stored codes are hashed."""
        return user_verification.hash_verification_code(code)
