"""Database-backed integration tests for instance persistence."""

from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.instance import create_instance, get_installation_profile
from app.model.instance import Instance


@pytest.mark.asyncio
async def test_create_and_fetch_installation_profile(session: AsyncSession) -> None:
    """Round-trip a realistic institutional configuration through SQLAlchemy."""
    created = await create_instance(
        session,
        {
            "instance_name": "LSFB Research",
            "institution_name": "University of Namur",
            "contact_email": "research@example.org",
            "domain": "research.example.org",
            "timezone": "Europe/Brussels",
            "default_language": "fr",
            "max_file_size_mb": Decimal("512.00"),
            "max_users": 250,
            "is_active": True,
        },
    )
    await session.flush()

    fetched = await get_installation_profile(session)

    assert fetched is not None
    assert fetched.instance_id == created.instance_id
    assert fetched.installation_id is not None
    assert fetched.institution_name == "University of Namur"
    assert fetched.max_file_size_mb == Decimal("512.00")


@pytest.mark.asyncio
async def test_installation_profile_is_none_for_empty_database(
    session: AsyncSession,
) -> None:
    """Represent the empty installation state explicitly."""
    assert await get_installation_profile(session) is None


@pytest.mark.asyncio
async def test_database_rejects_a_second_institution_profile(
    session: AsyncSession,
) -> None:
    """Make the deployment-level institution boundary a database invariant."""
    first = Instance(
        instance_name="First installation",
        institution_name="Institution A",
        contact_email="admin@a.example",
        domain="a.example",
        timezone="UTC",
    )
    second = Instance(
        instance_name="Second installation",
        institution_name="Institution B",
        contact_email="admin@b.example",
        domain="b.example",
        timezone="UTC",
    )
    session.add(first)
    await session.flush()
    session.add(second)

    with pytest.raises(IntegrityError):
        await session.flush()
