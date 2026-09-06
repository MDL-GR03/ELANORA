"""Durable delivery behavior for the PostgreSQL outbox."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import OutboxEvent
from app.service.outbox import (
    ACCOUNT_VERIFICATION_EMAIL,
    MAX_DELIVERY_ATTEMPTS,
    PASSWORD_RESET_EMAIL,
    DispatchResult,
    OutboxDispatcher,
    enqueue_account_verification_email,
    enqueue_existing_user_invitation_email,
    enqueue_password_reset_email,
)


@dataclass
class FakeEmailSender:
    """Capture delivery calls and optionally simulate a provider outage."""

    should_succeed: bool = True
    calls: list[dict[str, object]] = field(default_factory=list)

    async def send_existing_user_invitation_email(
        self,
        email: str,
        invitation_id: int,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        self.calls.append(
            {
                "email": email,
                "invitation_id": invitation_id,
                "sender_name": sender_name,
                "project_name": project_name,
                "custom_message": custom_message,
                "language": language,
            }
        )
        return self.should_succeed

    async def send_email_verification_code(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        self.calls.append(
            {
                "kind": "verification",
                "email": email,
                "username": username,
                "code": code,
                "language": language,
            }
        )
        return self.should_succeed

    async def send_password_reset_verification_email(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        self.calls.append(
            {
                "kind": "password_reset",
                "email": email,
                "username": username,
                "code": code,
                "language": language,
            }
        )
        return self.should_succeed


async def _enqueue(session: AsyncSession) -> OutboxEvent:
    event = await enqueue_existing_user_invitation_email(
        session,
        invitation_id=42,
        email="researcher@external.example",
        sender_name="Ada Admin",
        project_name="Signed corpus",
        custom_message="Please annotate session 12.",
        language="en",
    )
    await session.commit()
    return event


@pytest.mark.asyncio
async def test_dispatch_marks_event_published_and_scrubs_payload(
    session: AsyncSession,
) -> None:
    event = await _enqueue(session)
    sender = FakeEmailSender()

    result = await OutboxDispatcher(sender).dispatch_one(session)
    await session.refresh(event)

    assert result == DispatchResult.PUBLISHED
    assert event.published_at is not None
    assert event.attempts == 1
    assert event.payload == {}
    assert sender.calls == [
        {
            "email": "researcher@external.example",
            "invitation_id": 42,
            "sender_name": "Ada Admin",
            "project_name": "Signed corpus",
            "custom_message": "Please annotate session 12.",
            "language": "en",
        }
    ]
    assert await OutboxDispatcher(sender).dispatch_one(session) == DispatchResult.EMPTY


@pytest.mark.asyncio
async def test_failed_delivery_is_retained_for_a_later_retry(
    session: AsyncSession,
) -> None:
    event = await _enqueue(session)
    sender = FakeEmailSender(should_succeed=False)
    dispatcher = OutboxDispatcher(sender)

    assert await dispatcher.dispatch_one(session) == DispatchResult.FAILED
    await session.refresh(event)
    assert event.published_at is None
    assert event.attempts == 1
    assert event.payload["email"] == "researcher@external.example"

    sender.should_succeed = True
    assert await dispatcher.dispatch_one(session) == DispatchResult.PUBLISHED
    await session.refresh(event)
    assert event.published_at is not None
    assert event.attempts == 2
    assert event.payload == {}


@pytest.mark.asyncio
async def test_exhausted_event_does_not_block_the_dispatcher(
    session: AsyncSession,
) -> None:
    event = await _enqueue(session)
    event.attempts = MAX_DELIVERY_ATTEMPTS
    await session.commit()
    sender = FakeEmailSender()

    assert await OutboxDispatcher(sender).dispatch_one(session) == DispatchResult.EMPTY
    assert sender.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("enqueue", "event_type", "kind"),
    [
        (
            enqueue_account_verification_email,
            ACCOUNT_VERIFICATION_EMAIL,
            "verification",
        ),
        (enqueue_password_reset_email, PASSWORD_RESET_EMAIL, "password_reset"),
    ],
)
async def test_secret_account_email_is_encrypted_and_dispatched(
    session: AsyncSession,
    enqueue: Callable[..., Awaitable[OutboxEvent]],
    event_type: str,
    kind: str,
) -> None:
    event = await enqueue(
        session,
        user_id=7,
        email="researcher@example.org",
        username="researcher",
        code="314159",
        language="fr",
    )
    await session.commit()
    assert event.event_type == event_type
    assert "314159" not in str(event.payload)
    assert "researcher@example.org" not in str(event.payload)

    sender = FakeEmailSender()
    assert (
        await OutboxDispatcher(sender).dispatch_one(session) == DispatchResult.PUBLISHED
    )
    assert sender.calls == [
        {
            "kind": kind,
            "email": "researcher@example.org",
            "username": "researcher",
            "code": "314159",
            "language": "fr",
        }
    ]
