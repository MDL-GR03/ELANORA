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


def _database_url() -> str:
    database_url = os.environ.get("TEST_DATABASE_URL", DEFAULT_TEST_DATABASE_URL)
    if not database_url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("Integration tests require PostgreSQL through asyncpg")
    return database_url


@pytest_asyncio.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Provide a clean session backed by the migrated PostgreSQL test database."""
    engine = create_async_engine(_database_url(), pool_pre_ping=True)
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


@pytest_asyncio.fixture
async def session_factory(
    session: AsyncSession,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """Open independent sessions on separate connections for contention tests.

    Depends on ``session`` so the database is truncated before any worker
    connects. Each session from this factory is its own PostgreSQL backend, so
    row locks taken in one genuinely block another.
    """
    engine = create_async_engine(
        _database_url(), pool_pre_ping=True, pool_size=10, max_overflow=5
    )
    try:
        yield async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    finally:
        await engine.dispose()
