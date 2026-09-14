"""Invitation behavior at the local-installation collaboration boundary."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.invitation import (
    create_invitation,
    get_pending_invitations_by_email,
)
from app.crud.project import user_in_project
from app.model.audit_event import OutboxEvent
from app.model.enums import InvitationStatus, ProjectPermission, UserRole
from app.model.instance import Instance
from app.model.notification_preference import NotificationPreference
from app.model.project import Project
from app.model.user import User
from app.schema.requests.invitation import InvitationSendRequest
from app.service.invitation import InvitationService
from app.service.outbox import EXISTING_USER_INVITATION_EMAIL
from app.service.user import UserService


def _institution() -> Instance:
    return Instance(
        instance_name="Research Institute",
        institution_name="Research Institute",
        contact_email="admin@institute.example",
        domain="institute.example",
        timezone="UTC",
    )


def _user(username: str, email: str, institution: Instance) -> User:
    return User(
        username=username,
        email=email,
        hashed_password="unused-test-value",  # noqa: S106 - inert fixture
        first_name=username.title(),
        last_name="Researcher",
        affiliation="External University",
        department="Sign Linguistics",
        activation_code="fixture",
        instance=institution,
        role=UserRole.PUBLIC,
    )


@pytest.mark.asyncio
async def test_new_user_and_invitation_can_roll_back_as_one_transaction(
    session: AsyncSession,
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    project = Project(
        project_name="Atomic registration corpus",
        project_path="atomic-registration-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, project])
    await session.commit()
    invitation, _ = await create_invitation(
        session,
        sender.user_id,
        "new-researcher@external.example",
        project.project_id,
        ProjectPermission.WRITE,
    )
    invitation_id = invitation.invitation_id
    project_id = project.project_id

    user = await UserService.create_user(
        session,
        username="new-researcher",
        email="new-researcher@external.example",
        password="inert-integration-value",  # noqa: S106
        first_name="New",
        last_name="Researcher",
        affiliation="External University",
        department="Linguistics",
        instance_id=institution.instance_id,
        is_verified=True,
        commit=False,
    )
    assert await InvitationService().accept_invitation(
        session,
        invitation_id,
        user.user_id,
        commit=False,
    )
    user_id = user.user_id

    await session.rollback()

    assert (
        await session.scalar(
            select(User).where(User.email == "new-researcher@external.example")
        )
        is None
    )
    persisted_invitation = await session.get(type(invitation), invitation_id)
    assert persisted_invitation is not None
    assert persisted_invitation.status == InvitationStatus.PENDING
    assert not await user_in_project(session, user_id, project_id)


@pytest.mark.asyncio
async def test_validation_preview_does_not_grant_existing_user_access(
    session: AsyncSession,
) -> None:
    """A public GET with a bearer code must not alter project membership."""
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    recipient = _user("recipient", "recipient@external.example", institution)
    project = Project(
        project_name="Cross-team corpus",
        description="Invitation fixture",
        project_path="cross-team-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, recipient, project])
    await session.commit()

    invitation, raw_code = await create_invitation(
        db=session,
        sender_id=sender.user_id,
        receiver_email=recipient.email,
        project_id=project.project_id,
        project_permission=ProjectPermission.WRITE,
    )

    result = await InvitationService().validate_invitation(session, raw_code)
    await session.refresh(invitation)

    assert result.valid is True
    assert result.user_exists is True
    assert invitation.status == InvitationStatus.PENDING
    assert invitation.receiver is None
    assert not await user_in_project(session, recipient.user_id, project.project_id)


@pytest.mark.asyncio
async def test_pending_invitation_lookup_can_be_scoped_to_project(
    session: AsyncSession,
) -> None:
    """One recipient may legitimately be invited to multiple local projects."""
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    first = Project(
        project_name="First corpus",
        project_path="first-corpus",
        instance=institution,
    )
    second = Project(
        project_name="Second corpus",
        project_path="second-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, first, second])
    await session.commit()

    email = "guest@external.example"
    await create_invitation(
        session, sender.user_id, email, first.project_id, ProjectPermission.READ
    )

    assert len(await get_pending_invitations_by_email(session, email)) == 1
    assert (
        len(
            await get_pending_invitations_by_email(
                session, email, project_id=first.project_id
            )
        )
        == 1
    )
    assert not await get_pending_invitations_by_email(
        session, email, project_id=second.project_id
    )


@pytest.mark.asyncio
async def test_accept_invitation_atomically_grants_requested_permission(
    session: AsyncSession,
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    recipient = _user("recipient", "recipient@external.example", institution)
    project = Project(
        project_name="Permission corpus",
        project_path="permission-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, recipient, project])
    await session.commit()
    invitation, _ = await create_invitation(
        session,
        sender.user_id,
        recipient.email,
        project.project_id,
        ProjectPermission.WRITE,
    )

    assert await InvitationService().accept_invitation(
        session, invitation.invitation_id, recipient.user_id
    )
    await session.refresh(invitation)
    membership = await user_in_project(session, recipient.user_id, project.project_id)

    assert invitation.status == InvitationStatus.ACCEPTED
    assert invitation.receiver == recipient.user_id
    assert membership is not None
    assert membership.permission == ProjectPermission.WRITE


@pytest.mark.asyncio
async def test_accept_invitation_rejects_wrong_or_expired_recipient(
    session: AsyncSession,
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    recipient = _user("recipient", "recipient@external.example", institution)
    stranger = _user("stranger", "stranger@external.example", institution)
    project = Project(
        project_name="Protected corpus",
        project_path="protected-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, recipient, stranger, project])
    await session.commit()
    invitation, _ = await create_invitation(
        session, sender.user_id, recipient.email, project.project_id
    )
    service = InvitationService()
    assert not await service.accept_invitation(
        session, invitation.invitation_id, stranger.user_id
    )
    invitation.expires_at = datetime.now() - timedelta(minutes=1)
    await session.commit()
    assert not await service.accept_invitation(
        session, invitation.invitation_id, recipient.user_id
    )
    await session.refresh(invitation)

    assert invitation.status == InvitationStatus.PENDING
    assert not await user_in_project(session, recipient.user_id, project.project_id)


@pytest.mark.asyncio
async def test_membership_failure_does_not_consume_invitation(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    recipient = _user("recipient", "recipient@external.example", institution)
    project = Project(
        project_name="Atomic corpus",
        project_path="atomic-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, recipient, project])
    await session.commit()
    invitation, _ = await create_invitation(
        session, sender.user_id, recipient.email, project.project_id
    )
    recipient_id = recipient.user_id
    project_id = project.project_id

    async def fail_membership(*args: object, **kwargs: object) -> None:
        raise RuntimeError("simulated membership failure")

    monkeypatch.setattr("app.service.invitation.add_user_to_project", fail_membership)

    assert not await InvitationService().accept_invitation(
        session, invitation.invitation_id, recipient_id
    )
    await session.refresh(invitation)

    assert invitation.status == InvitationStatus.PENDING
    assert invitation.receiver is None
    assert not await user_in_project(session, recipient_id, project_id)


@pytest.mark.asyncio
async def test_existing_user_invitation_and_email_request_commit_together(
    session: AsyncSession,
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    recipient = _user("recipient", "recipient@external.example", institution)
    project = Project(
        project_name="Queued corpus",
        project_path="queued-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, recipient, project])
    await session.flush()
    session.add(NotificationPreference(user_id=recipient.user_id, email_enabled=True))
    await session.commit()

    result = await InvitationService().send_invitation(
        session,
        sender.user_id,
        InvitationSendRequest(
            receiver_email=recipient.email,
            project_name=project.project_name,
            project_permission=ProjectPermission.READ,
            message="Please review this corpus.",
            language="en",
        ),
    )
    await session.commit()
    event = await session.scalar(select(OutboxEvent))

    assert result.success is True
    assert result.invitation_id is not None
    assert event is not None
    assert event.aggregate_id == str(result.invitation_id)
    assert event.event_type == EXISTING_USER_INVITATION_EMAIL
    assert event.payload["email"] == recipient.email


@pytest.mark.asyncio
async def test_new_user_email_failure_does_not_leave_unusable_invitation(
    session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    institution = _institution()
    sender = _user("sender", "sender@institute.example", institution)
    project = Project(
        project_name="Undelivered corpus",
        project_path="undelivered-corpus",
        instance=institution,
    )
    session.add_all([institution, sender, project])
    await session.commit()
    project_id = project.project_id

    async def fail_delivery(*args: object, **kwargs: object) -> bool:
        return False

    service = InvitationService()
    monkeypatch.setattr(service.email_service, "send_invitation_email", fail_delivery)
    result = await service.send_invitation(
        session,
        sender.user_id,
        InvitationSendRequest(
            receiver_email="new.researcher@external.example",
            project_name=project.project_name,
        ),
    )

    invitations = await get_pending_invitations_by_email(
        session, "new.researcher@external.example", project_id=project_id
    )
    assert result.success is False
    assert invitations == []
