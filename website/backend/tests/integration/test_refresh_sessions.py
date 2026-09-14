import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_refresh_token
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.user import User
from app.schema.common.token import TokenData
from app.service.refresh_session import create_refresh_session, revoke_refresh_session
from app.service.user import UserService


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

    first = await UserService.refresh_user_tokens(session, original)
    assert first["success"] is True

    replay = await UserService.refresh_user_tokens(session, original)
    assert replay["success"] is False

    rotated = str(first["refresh_token"])
    await revoke_refresh_session(session, session_id)
    revoked = await UserService.refresh_user_tokens(session, rotated)
    assert revoked["success"] is False
