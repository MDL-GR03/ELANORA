import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.core.jwt import create_refresh_token
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.refresh_session import RefreshSession
from app.model.user import User
from app.schema.common.token import TokenData
from app.service import user_passwords, user_sessions
from app.service.refresh_session import (
    create_refresh_session,
    delete_expired_refresh_sessions,
    revoke_refresh_session,
)
from app.utils import password_hashing


@pytest.mark.asyncio
async def test_refresh_token_rotation_rejects_replay_and_revocation(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = User(
        username="researcher",
        email="researcher@example.org",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Ada",
        last_name="Researcher",
        affiliation="Institute",
        department="Linguistics",
        activation_code="",
        is_verified_account=True,
        instance=institution,
        role=UserRole.PUBLIC,
    )
    session.add_all([institution, user])
    await session.flush()
    session_id = uuid.uuid4()
    original = create_refresh_token(
        TokenData(sub=str(user.user_id), session_id=str(session_id))
    )
    await create_refresh_session(session, user.user_id, session_id, original)
    await session.commit()

    first = await user_sessions.refresh_user_tokens(session, original)

    with pytest.raises(ElanoraError) as replay:
        await user_sessions.refresh_user_tokens(session, original)
    assert replay.value.code == ErrorCode.SESSION_REFRESH_FAILED

    await revoke_refresh_session(session, session_id)
    with pytest.raises(ElanoraError):
        await user_sessions.refresh_user_tokens(session, first.refresh_token)


@pytest.mark.asyncio
async def test_password_change_revokes_every_active_refresh_session(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = User(
        username="researcher",
        email="researcher@example.org",
        hashed_password=password_hashing.hash_password("old-password-123"),
        first_name="Ada",
        last_name="Researcher",
        affiliation="Institute",
        department="Linguistics",
        activation_code="",
        is_verified_account=True,
        instance=institution,
        role=UserRole.PUBLIC,
    )
    session.add_all([institution, user])
    await session.flush()

    tokens: list[str] = []
    for _ in range(2):
        session_id = uuid.uuid4()
        token = create_refresh_token(
            TokenData(sub=str(user.user_id), session_id=str(session_id))
        )
        await create_refresh_session(session, user.user_id, session_id, token)
        tokens.append(token)
    await session.commit()

    await user_passwords.change_password(
        session, user, "old-password-123", "new-password-456"
    )

    stored_sessions = (
        await session.execute(
            select(RefreshSession).where(RefreshSession.user_id == user.user_id)
        )
    ).scalars()
    assert all(item.revoked_at is not None for item in stored_sessions)
    for token in tokens:
        with pytest.raises(ElanoraError):
            await user_sessions.refresh_user_tokens(session, token)


@pytest.mark.asyncio
async def test_expired_refresh_session_cleanup_preserves_current_sessions(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = User(
        username="researcher",
        email="researcher@example.org",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Ada",
        last_name="Researcher",
        affiliation="Institute",
        department="Linguistics",
        activation_code="",
        is_verified_account=True,
        instance=institution,
        role=UserRole.PUBLIC,
    )
    session.add_all([institution, user])
    await session.flush()
    now = datetime.now(UTC)
    expired_id = uuid.uuid4()
    current_id = uuid.uuid4()
    session.add_all(
        [
            RefreshSession(
                session_id=expired_id,
                user_id=user.user_id,
                token_hash="a" * 64,
                expires_at=now - timedelta(seconds=1),
            ),
            RefreshSession(
                session_id=current_id,
                user_id=user.user_id,
                token_hash="b" * 64,
                expires_at=now + timedelta(days=1),
            ),
        ]
    )
    await session.flush()

    deleted = await delete_expired_refresh_sessions(session, now=now)
    await session.commit()

    remaining_ids = set(
        (await session.execute(select(RefreshSession.session_id))).scalars()
    )
    assert deleted == 1
    assert expired_id not in remaining_ids
    assert current_id in remaining_ids
