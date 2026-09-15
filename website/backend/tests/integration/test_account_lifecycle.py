"""Administrator suspension and restoration of institution accounts."""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.jwt import create_refresh_token
from app.crud.user import get_all_active_users, get_all_users
from app.model.audit_event import AuditEvent
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.refresh_session import RefreshSession
from app.model.user import User
from app.schema.common.token import TokenData
from app.service.refresh_session import create_refresh_session
from app.service.user import (
    AccountNotFoundError,
    AdministratorNoLongerActiveError,
    RedundantAccountStatusError,
    SelfAccountStatusError,
    UserService,
)

RESEARCHER_PASSWORD = "researcher-password-123"  # noqa: S105


def _institution(domain: str = "example.org") -> Instance:
    return Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email=f"admin@{domain}",
        domain=domain,
        timezone="UTC",
    )


def _user(
    institution: Instance,
    *,
    username: str,
    role: UserRole = UserRole.PUBLIC,
    is_active: bool = True,
) -> User:
    return User(
        username=username,
        email=f"{username}@example.org",
        hashed_password=UserService.hash_password(RESEARCHER_PASSWORD),
        first_name="Ada",
        last_name=username.capitalize(),
        affiliation="Institute",
        department="Linguistics",
        activation_code="",
        is_verified_account=True,
        is_active=is_active,
        instance=institution,
        role=role,
    )


async def _seed(session: AsyncSession) -> tuple[Instance, User, User]:
    institution = _institution()
    admin = _user(institution, username="curator", role=UserRole.ADMIN)
    researcher = _user(institution, username="researcher")
    session.add_all([institution, admin, researcher])
    await session.commit()
    return institution, admin, researcher


@pytest.mark.asyncio
async def test_suspension_signs_the_account_out_everywhere(
    session: AsyncSession,
) -> None:
    _, admin, researcher = await _seed(session)
    tokens = []
    for _ in range(2):
        session_id = uuid.uuid4()
        token = create_refresh_token(
            TokenData(sub=str(researcher.user_id), session_id=str(session_id))
        )
        await create_refresh_session(session, researcher.user_id, session_id, token)
        tokens.append(token)
    await session.commit()

    updated = await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=False,
        reason="Left the institution",
    )

    assert updated.is_active is False
    for token in tokens:
        assert (await UserService.refresh_user_tokens(session, token))[
            "success"
        ] is False
    revoked = (
        (
            await session.execute(
                select(RefreshSession).where(
                    RefreshSession.user_id == researcher.user_id,
                    RefreshSession.revoked_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    )
    assert revoked == []


@pytest.mark.asyncio
async def test_suspended_account_cannot_log_in_with_valid_password(
    session: AsyncSession,
) -> None:
    _, admin, researcher = await _seed(session)

    before = await UserService.login_user(
        session, researcher.username, RESEARCHER_PASSWORD
    )
    assert before["success"] is True

    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=False,
        reason="Offboarding",
    )

    refused = await UserService.login_user(
        session, researcher.username, RESEARCHER_PASSWORD
    )
    assert refused["success"] is False
    assert "suspended" in refused["message"]
    assert "user" not in refused


@pytest.mark.asyncio
async def test_restoration_allows_login_again(session: AsyncSession) -> None:
    _, admin, researcher = await _seed(session)
    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=False,
        reason="Temporary leave",
    )

    restored = await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=True,
        reason="Returned from leave",
    )

    assert restored.is_active is True
    allowed = await UserService.login_user(
        session, researcher.username, RESEARCHER_PASSWORD
    )
    assert allowed["success"] is True


@pytest.mark.asyncio
async def test_status_changes_are_recorded_in_the_audit_log(
    session: AsyncSession,
) -> None:
    _, admin, researcher = await _seed(session)
    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=False,
        reason="  Policy violation  ",
    )
    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=True,
        reason="Appeal upheld",
    )

    events = (
        (
            await session.execute(
                select(AuditEvent)
                .where(AuditEvent.resource_id == str(researcher.user_id))
                .order_by(AuditEvent.occurred_at)
            )
        )
        .scalars()
        .all()
    )

    assert [event.action for event in events] == [
        "account.suspended",
        "account.reactivated",
    ]
    assert all(event.actor_user_id == admin.user_id for event in events)
    assert all(event.resource_type == "user" for event in events)
    assert events[0].details["reason"] == "Policy violation"


@pytest.mark.asyncio
async def test_administrators_cannot_suspend_themselves(session: AsyncSession) -> None:
    _, admin, _ = await _seed(session)

    with pytest.raises(SelfAccountStatusError):
        await UserService.set_account_active(
            session,
            actor=admin,
            target_user_id=admin.user_id,
            is_active=False,
            reason="Accidental self-lockout",
        )


@pytest.mark.asyncio
async def test_an_administrator_suspended_mid_request_cannot_complete_it(
    session: AsyncSession,
) -> None:
    """Authorization is checked when a request starts; suspension can land later.

    The deputy's request was authorized while they were still active. It must
    not complete once another administrator has suspended them in the meantime.
    """
    institution, admin, researcher = await _seed(session)
    deputy = _user(institution, username="deputy", role=UserRole.ADMIN)
    session.add(deputy)
    await session.commit()

    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=deputy.user_id,
        is_active=False,
        reason="Role handover",
    )

    # `deputy` is the object the request guard loaded before the suspension.
    with pytest.raises(AdministratorNoLongerActiveError):
        await UserService.set_account_active(
            session,
            actor=deputy,
            target_user_id=researcher.user_id,
            is_active=False,
            reason="Issued by a suspended administrator",
        )

    await session.refresh(researcher)
    assert researcher.is_active is True


@pytest.mark.asyncio
async def test_the_institution_keeps_an_administrator_after_any_suspension(
    session: AsyncSession,
) -> None:
    institution, admin, _ = await _seed(session)
    deputy = _user(institution, username="deputy", role=UserRole.ADMIN)
    session.add(deputy)
    await session.commit()

    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=deputy.user_id,
        is_active=False,
        reason="Role handover",
    )

    active_admins = [
        account
        for account in await get_all_active_users(session, institution.instance_id)
        if account.role == UserRole.ADMIN
    ]
    assert [account.user_id for account in active_admins] == [admin.user_id]


@pytest.mark.asyncio
async def test_repeating_the_current_status_is_rejected(session: AsyncSession) -> None:
    _, admin, researcher = await _seed(session)

    with pytest.raises(RedundantAccountStatusError):
        await UserService.set_account_active(
            session,
            actor=admin,
            target_user_id=researcher.user_id,
            is_active=True,
            reason="No change",
        )


@pytest.mark.asyncio
async def test_listing_and_status_changes_stay_inside_the_installation(
    session: AsyncSession,
) -> None:
    # One installation hosts exactly one institution, so scoping is verified
    # through the administrator's own instance rather than a second Instance
    # row, which the "uq_instance_singleton_key" constraint forbids.
    institution, admin, _ = await _seed(session)

    listed = await get_all_users(session, institution.instance_id)
    assert {account.username for account in listed} == {"curator", "researcher"}
    assert await get_all_users(session, institution.instance_id + 1) == []

    with pytest.raises(AccountNotFoundError):
        await UserService.set_account_active(
            session,
            actor=admin,
            target_user_id=999_999,
            is_active=False,
            reason="Unknown account",
        )


@pytest.mark.asyncio
async def test_suspended_accounts_are_listed_but_excluded_from_active_users(
    session: AsyncSession,
) -> None:
    institution, admin, researcher = await _seed(session)
    await UserService.set_account_active(
        session,
        actor=admin,
        target_user_id=researcher.user_id,
        is_active=False,
        reason="Offboarding",
    )

    every = await get_all_users(session, institution.instance_id)
    active = await get_all_active_users(session, institution.instance_id)

    assert {account.username for account in every} == {"curator", "researcher"}
    assert {account.username for account in active} == {"curator"}
