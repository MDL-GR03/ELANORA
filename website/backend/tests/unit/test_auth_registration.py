from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import auth_registration
from app.schema.requests.register_with_invitation import RegisterWithInvitationRequest
from app.service import (
    invitation_decisions,
    invitation_notifications,
    invitation_queries,
    user_registration,
)


@pytest.mark.asyncio
async def test_registration_rolls_back_when_invitation_cannot_be_redeemed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    invitation = SimpleNamespace(
        invitation_id=9,
        project_id=4,
        receiver_email="researcher@example.org",
    )
    monkeypatch.setattr(
        invitation_queries,
        "validate_invitation",
        AsyncMock(return_value=SimpleNamespace(valid=True, invitation=invitation)),
    )
    monkeypatch.setattr(
        auth_registration,
        "get_project_by_id",
        AsyncMock(return_value=SimpleNamespace(instance_id=2)),
    )
    creator = AsyncMock(
        return_value=SimpleNamespace(
            user_id=7,
            username="researcher",
            email="researcher@example.org",
        )
    )
    monkeypatch.setattr(user_registration, "create_user", creator)
    accepter = AsyncMock(return_value=False)
    monkeypatch.setattr(invitation_decisions, "accept_invitation", accepter)
    request = RegisterWithInvitationRequest(
        invitation_code="valid-code",
        first_name="Ada",
        last_name="Researcher",
        username="researcher",
        email="researcher@example.org",
        password="tidal marsh 7 lanterns",  # noqa: S106 - inert test value
        affiliation="Research Institute",
        department="Linguistics",
    )

    with pytest.raises(HTTPException) as caught:
        await auth_registration.register(request, db)

    assert caught.value.status_code == 409
    assert creator.await_args.kwargs["commit"] is False
    assert accepter.await_args.kwargs["commit"] is False
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_registration_commits_user_and_invitation_together(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    invitation = SimpleNamespace(
        invitation_id=9,
        project_id=4,
        receiver_email="researcher@example.org",
    )
    monkeypatch.setattr(
        invitation_queries,
        "validate_invitation",
        AsyncMock(return_value=SimpleNamespace(valid=True, invitation=invitation)),
    )
    monkeypatch.setattr(
        auth_registration,
        "get_project_by_id",
        AsyncMock(return_value=SimpleNamespace(instance_id=2)),
    )
    monkeypatch.setattr(
        user_registration,
        "create_user",
        AsyncMock(
            return_value=SimpleNamespace(
                user_id=7,
                username="researcher",
                email="researcher@example.org",
            )
        ),
    )
    monkeypatch.setattr(
        invitation_decisions, "accept_invitation", AsyncMock(return_value=True)
    )
    notifier = AsyncMock()
    monkeypatch.setattr(
        invitation_notifications, "notify_project_admins_member_joined", notifier
    )
    request = RegisterWithInvitationRequest(
        invitation_code="valid-code",
        first_name="Ada",
        last_name="Researcher",
        username="researcher",
        email="researcher@example.org",
        password="tidal marsh 7 lanterns",  # noqa: S106 - inert test value
        affiliation="Research Institute",
        department="Linguistics",
    )

    response = await auth_registration.register(request, db)

    assert response.user_id == 7
    assert response.requires_activation is False
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()
    notifier.assert_awaited_once()
