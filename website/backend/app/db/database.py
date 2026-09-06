"""Async SQLAlchemy engine and session lifecycle."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.centralized_logging import get_logger
from app.core.settings import get_settings

logger = get_logger()


class Base(DeclarativeBase):
    """Declarative base shared by all persisted models."""


_engine: AsyncEngine | None = None
_session_maker: async_sessionmaker[AsyncSession] | None = None


def build_database_url() -> str | None:
    """Resolve the configured URL while retaining the legacy optional contract."""
    try:
        return get_settings().resolved_database_url
    except RuntimeError:
        return None


def create_engine(database_url: str) -> AsyncEngine:
    """Create an engine without storing it in process-global state."""
    return create_async_engine(
        database_url,
        echo=get_settings().db_echo,
        pool_pre_ping=True,
    )


def init_database(database_url: str | None = None) -> AsyncEngine:
    """Initialize the process-wide engine and session factory exactly once."""
    global _engine, _session_maker  # noqa: PLW0603 - application lifecycle state
    if _engine is not None:
        return _engine
    url = database_url or build_database_url()
    if not url:
        raise RuntimeError("DATABASE_URL is not set or incomplete")
    _engine = create_engine(url)
    _session_maker = async_sessionmaker(
        bind=_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    logger.info("Database engine initialized")
    return _engine


def get_engine(
    database_url: str | None = None, echo: bool | None = None
) -> AsyncEngine:
    """Return the application engine or a caller-owned engine for an explicit URL."""
    if database_url is not None:
        return create_async_engine(
            database_url,
            echo=get_settings().db_echo if echo is None else echo,
            pool_pre_ping=True,
        )
    return init_database()


def get_session_maker(
    engine: AsyncEngine | None = None,
) -> async_sessionmaker[AsyncSession]:
    """Return a factory bound to a caller engine or the application engine."""
    if engine is not None:
        return async_sessionmaker(engine, expire_on_commit=False, autoflush=False)
    if _session_maker is None:
        init_database()
    if _session_maker is None:
        raise RuntimeError("database session factory failed to initialize")
    return _session_maker


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield one request-scoped session from the shared connection pool."""
    session_maker = get_session_maker()
    async with session_maker() as session:
        try:
            yield session
        except BaseException:
            await session.rollback()
            raise


async def close_database() -> None:
    """Dispose pooled connections during application shutdown."""
    global _engine, _session_maker  # noqa: PLW0603 - application lifecycle state
    if _engine is not None:
        await _engine.dispose()
    _engine = None
    _session_maker = None
