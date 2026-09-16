"""Create this installation's institution profile and administrator safely."""

import argparse
import asyncio
import getpass
import sys
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import close_database, get_session_maker, init_database
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.user import User
from app.utils import password_hashing

MINIMUM_BOOTSTRAP_PASSWORD_LENGTH = 12


@dataclass(frozen=True, slots=True)
class BootstrapConfig:
    """Non-secret institutional bootstrap values."""

    instance_name: str
    institution_name: str
    contact_email: str
    domain: str
    timezone: str
    default_language: str
    admin_username: str
    admin_email: str
    admin_first_name: str
    admin_last_name: str
    admin_affiliation: str
    admin_department: str
    primary_color: str = "#2563eb"
    secondary_color: str = "#0f766e"
    accent_color: str = "#d97706"


async def bootstrap(
    db: AsyncSession, config: BootstrapConfig, password: str
) -> tuple[Instance, User]:
    """Create the only institution profile and initial admin atomically."""
    if len(password) < MINIMUM_BOOTSTRAP_PASSWORD_LENGTH:
        raise ValueError(
            f"administrator password must have at least {MINIMUM_BOOTSTRAP_PASSWORD_LENGTH} characters"
        )
    existing_instances = await db.scalar(select(func.count()).select_from(Instance))
    existing_users = await db.scalar(select(func.count()).select_from(User))
    if existing_instances or existing_users:
        raise RuntimeError("bootstrap refused: an instance or user already exists")

    instance = Instance(
        instance_name=config.instance_name,
        institution_name=config.institution_name,
        contact_email=config.contact_email,
        domain=config.domain,
        timezone=config.timezone,
        default_language=config.default_language,
        primary_color=config.primary_color,
        secondary_color=config.secondary_color,
        accent_color=config.accent_color,
    )
    user = User(
        username=config.admin_username,
        email=config.admin_email,
        hashed_password=password_hashing.hash_password(password),
        first_name=config.admin_first_name,
        last_name=config.admin_last_name,
        affiliation=config.admin_affiliation,
        department=config.admin_department,
        activation_code="",
        is_verified_account=True,
        role=UserRole.ADMIN,
        instance=instance,
    )
    db.add_all([instance, user])
    await db.commit()
    await db.refresh(instance)
    await db.refresh(user)
    return instance, user


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--instance-name", required=True)
    parser.add_argument("--institution-name", required=True)
    parser.add_argument("--contact-email", required=True)
    parser.add_argument("--domain", required=True)
    parser.add_argument("--timezone", default="UTC")
    parser.add_argument("--default-language", default="en")
    parser.add_argument("--admin-username", required=True)
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-first-name", required=True)
    parser.add_argument("--admin-last-name", required=True)
    parser.add_argument("--admin-affiliation", required=True)
    parser.add_argument("--admin-department", required=True)
    parser.add_argument(
        "--password-stdin",
        action="store_true",
        help="Read the administrator password from standard input, for guided setup",
    )
    return parser.parse_args()


def read_password(*, from_stdin: bool) -> str:
    """Take the first administrator's password from setup or from a person.

    Guided setup has no terminal to prompt at, so it pipes the password in.
    Someone running this by hand types it twice instead.
    """
    if from_stdin:
        password = sys.stdin.readline().strip()
    else:
        password = getpass.getpass("Initial administrator password: ")
        if password != getpass.getpass("Confirm administrator password: "):
            raise ValueError("password confirmation does not match")
    if not password:
        raise ValueError("administrator password must not be empty")
    return password


async def _main() -> None:
    arguments = _arguments()
    password = read_password(from_stdin=arguments.password_stdin)
    settings = vars(arguments) | {}
    settings.pop("password_stdin")
    config = BootstrapConfig(**settings)

    init_database()
    try:
        async with get_session_maker()() as db:
            instance, user = await bootstrap(db, config, password)
            print(
                f"Created institution {instance.instance_name!r} and administrator {user.username!r}."
            )
    finally:
        await close_database()


def main() -> None:
    """Run the interactive administrative bootstrap command."""
    asyncio.run(_main())
