"""Persistence and rotation rules for browser refresh sessions."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import REFRESH_TOKEN_EXPIRE_DAYS
from app.model.refresh_session import RefreshSession

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_session(
    db: AsyncSession, user_id: int, session_id: uuid.UUID, token: str
) -> RefreshSession:
    await delete_expired_refresh_sessions(db)
    session = RefreshSession(
        session_id=session_id,
        user_id=user_id,
        token_hash=hash_refresh_token(token),
        expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(session)
    await db.flush()
    return session


async def rotate_refresh_session(
    db: AsyncSession, session_id: uuid.UUID, presented_token: str, new_token: str
) -> bool:
    session = await db.scalar(
        select(RefreshSession)
        .where(RefreshSession.session_id == session_id)
        .with_for_update()
    )
    now = datetime.now(UTC)
    if (
        session is None
        or session.revoked_at is not None
        or session.expires_at <= now
        or not secrets.compare_digest(
            session.token_hash, hash_refresh_token(presented_token)
        )
    ):
        return False
    session.token_hash = hash_refresh_token(new_token)
    session.rotated_at = now
    session.expires_at = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    await db.flush()
    return True


async def revoke_refresh_session(db: AsyncSession, session_id: uuid.UUID) -> None:
    session = await db.get(RefreshSession, session_id)
    if session is not None and session.revoked_at is None:
        session.revoked_at = datetime.now(UTC)
        await db.commit()


async def revoke_all_refresh_sessions(db: AsyncSession, user_id: int) -> int:
    """Revoke every active browser session after an account security change."""
    result = await db.execute(
        update(RefreshSession)
        .where(
            RefreshSession.user_id == user_id,
            RefreshSession.revoked_at.is_(None),
        )
        .values(revoked_at=datetime.now(UTC))
    )
    return int(cast("CursorResult[Any]", result).rowcount or 0)


async def delete_expired_refresh_sessions(
    db: AsyncSession, *, now: datetime | None = None
) -> int:
    """Delete expired session metadata during normal login activity."""
    result = await db.execute(
        delete(RefreshSession).where(
            RefreshSession.expires_at <= (now or datetime.now(UTC))
        )
    )
    return int(cast("CursorResult[Any]", result).rowcount or 0)
