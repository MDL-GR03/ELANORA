"""Shared PostgreSQL fixtures for database integration tests."""

import os
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.database import Base

DEFAULT_TEST_DATABASE_URL = (
    "postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test"
)


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide a clean session backed by the migrated PostgreSQL test database."""
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Integration tests require PostgreSQL through asyncpg")

    engine = create_async_engine(database_url, pool_pre_ping=True)
    table_names = ", ".join(
        f'"{table.name}"' for table in reversed(Base.metadata.sorted_tables)
    )
    async with engine.begin() as connection:
        await connection.execute(
            text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE")
        )

    factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    async with factory() as database_session:
        yield database_session
        await database_session.rollback()
    await engine.dispose()
