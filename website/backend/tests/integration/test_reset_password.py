"""Administrative password recovery tests."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import BootstrapConfig, bootstrap
from app.cli.reset_password import reset_password
from app.core.errors import ElanoraError
from app.core.jwt import create_refresh_token
from app.model.refresh_session import RefreshSession
from app.schema.common.token import TokenData
from app.service import user_sessions
from app.service.refresh_session import create_refresh_session
from app.utils import password_hashing


@pytest.mark.asyncio
async def test_reset_password_replaces_hash_and_preserves_account(
    session: AsyncSession,
) -> None:
    config = BootstrapConfig(
        instance_name="Research instance",
        institution_name="Research institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
        default_language="en",
        admin_username="administrator",
        admin_email="administrator@example.org",
        admin_first_name="Local",
        admin_last_name="Admin",
        admin_affiliation="Research institute",
        admin_department="Research IT",
    )
    _, original = await bootstrap(session, config, "tidal marsh 7 lanterns")
    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(
        TokenData(sub=str(original.user_id), session_id=str(session_id))
    )
    await create_refresh_session(session, original.user_id, session_id, refresh_token)
    await session.commit()

    updated = await reset_password(session, "administrator", "quiet river bends west")

    assert updated.user_id == original.user_id
    assert password_hashing.verify_password(
        "quiet river bends west", updated.hashed_password
    )
    assert not password_hashing.verify_password(
        "tidal marsh 7 lanterns", updated.hashed_password
    )
    stored_session = await session.scalar(
        select(RefreshSession).where(RefreshSession.session_id == session_id)
    )
    assert stored_session is not None
    assert stored_session.revoked_at is not None
    with pytest.raises(ElanoraError):
        await user_sessions.refresh_user_tokens(session, refresh_token)
