"""Set a local ELANORA user's password from an administrative shell."""

import argparse
import asyncio
import getpass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import MINIMUM_BOOTSTRAP_PASSWORD_LENGTH
from app.db.database import close_database, get_session_maker, init_database
from app.model.user import User
from app.service.refresh_session import revoke_all_refresh_sessions
from app.utils import password_hashing


async def reset_password(db: AsyncSession, username: str, password: str) -> User:
    """Replace one user's password hash without changing any other account data."""
    if len(password) < MINIMUM_BOOTSTRAP_PASSWORD_LENGTH:
        raise ValueError(
            f"password must have at least {MINIMUM_BOOTSTRAP_PASSWORD_LENGTH} characters"
        )
    user = await db.scalar(select(User).where(User.username == username))
    if user is None:
        raise ValueError(f"user {username!r} does not exist")
    user.hashed_password = password_hashing.hash_password(password)
    await revoke_all_refresh_sessions(db, user.user_id)
    await db.commit()
    await db.refresh(user)
    return user


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--username", required=True)
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    password = getpass.getpass("New password: ")
    confirmation = getpass.getpass("Confirm new password: ")
    if password != confirmation:
        raise ValueError("password confirmation does not match")

    init_database()
    try:
        async with get_session_maker()() as db:
            user = await reset_password(db, arguments.username, password)
    finally:
        await close_database()
    print(f"Updated password for {user.username!r}.")


def main() -> None:
    """Run the interactive password reset command."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
