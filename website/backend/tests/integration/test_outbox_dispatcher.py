"""Durable delivery behavior for the PostgreSQL outbox."""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import OutboxEvent
from app.service.outbox import (
    ACCOUNT_VERIFICATION_EMAIL,
    FAILED_EVENT_RETENTION_DAYS,
    MAX_DELIVERY_ATTEMPTS,
    PASSWORD_RESET_EMAIL,
    DispatchResult,
    OutboxDispatcher,
    count_pending_events,
    count_permanently_failed_events,
    enqueue_account_verification_email,
    enqueue_existing_user_invitation_email,
    enqueue_password_reset_email,
    oldest_pending_event_at,
    purge_failed_events,
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


@pytest.mark.asyncio
async def test_the_last_failed_attempt_discards_the_recipient_details(
    session: AsyncSession,
) -> None:
    """A record that will never be retried must not keep personal data."""
    event = await _enqueue(session)
    event.attempts = MAX_DELIVERY_ATTEMPTS - 1
    await session.commit()
    sender = FakeEmailSender(should_succeed=False)

    result = await OutboxDispatcher(sender).dispatch_one(session)
    await session.refresh(event)

    assert result == DispatchResult.EXHAUSTED
    assert event.attempts == MAX_DELIVERY_ATTEMPTS
    assert event.published_at is None
    assert event.payload == {}
    # The fact of the failure survives so an administrator can act on it.
    assert event.event_type
    assert event.aggregate_id


@pytest.mark.asyncio
async def test_an_earlier_failure_keeps_the_payload_for_the_next_attempt(
    session: AsyncSession,
) -> None:
    event = await _enqueue(session)
    sender = FakeEmailSender(should_succeed=False)

    result = await OutboxDispatcher(sender).dispatch_one(session)
    await session.refresh(event)

    assert result == DispatchResult.FAILED
    assert event.attempts == 1
    assert event.payload != {}


@pytest.mark.asyncio
async def test_failed_records_are_purged_only_after_the_retention_window(
    session: AsyncSession,
) -> None:
    recent = await _enqueue(session)
    stale = await _enqueue(session)
    for event in (recent, stale):
        event.attempts = MAX_DELIVERY_ATTEMPTS
        event.payload = {}
    stale.occurred_at = datetime.now(UTC) - timedelta(
        days=FAILED_EVENT_RETENTION_DAYS + 1
    )
    await session.commit()

    removed = await purge_failed_events(session)

    assert removed == 1
    remaining = await count_permanently_failed_events(session)
    assert remaining == 1
    assert await session.get(OutboxEvent, recent.event_id) is not None
    assert await session.get(OutboxEvent, stale.event_id) is None


@pytest.mark.asyncio
async def test_purging_never_removes_deliverable_or_published_records(
    session: AsyncSession,
) -> None:
    pending = await _enqueue(session)
    published = await _enqueue(session)
    published.published_at = datetime.now(UTC)
    published.payload = {}
    long_ago = datetime.now(UTC) - timedelta(days=FAILED_EVENT_RETENTION_DAYS * 10)
    pending.occurred_at = long_ago
    published.occurred_at = long_ago
    await session.commit()

    removed = await purge_failed_events(session)

    assert removed == 0
    assert await session.get(OutboxEvent, pending.event_id) is not None
    assert await session.get(OutboxEvent, published.event_id) is not None


@pytest.mark.asyncio
async def test_a_negative_retention_window_is_refused(session: AsyncSession) -> None:
    with pytest.raises(ValueError, match="cannot be negative"):
        await purge_failed_events(session, retention_days=-1)


@pytest.mark.asyncio
async def test_delivery_counts_separate_pending_from_given_up(
    session: AsyncSession,
) -> None:
    pending = await _enqueue(session)
    given_up = await _enqueue(session)
    given_up.attempts = MAX_DELIVERY_ATTEMPTS
    given_up.payload = {}
    queued_at = datetime.now(UTC) - timedelta(hours=3)
    pending.occurred_at = queued_at
    await session.commit()

    assert await count_pending_events(session) == 1
    assert await count_permanently_failed_events(session) == 1

    oldest = await oldest_pending_event_at(session)
    assert oldest is not None
    assert abs((oldest - queued_at).total_seconds()) < 1


@pytest.mark.asyncio
async def test_an_exhausted_record_does_not_stop_the_batch(
    session: AsyncSession,
) -> None:
    """Giving up on one message must not strand the ones behind it."""
    doomed = await _enqueue(session)
    doomed.attempts = MAX_DELIVERY_ATTEMPTS - 1
    doomed.occurred_at = datetime.now(UTC) - timedelta(hours=1)
    await session.commit()
    await _enqueue(session)

    sender = FakeEmailSender(should_succeed=False)
    await OutboxDispatcher(sender).dispatch_pending(session, limit=5)
    await session.refresh(doomed)

    assert doomed.attempts == MAX_DELIVERY_ATTEMPTS
    assert doomed.payload == {}
    # The dispatcher reached the queued message behind it in the same batch.
    assert len(sender.calls) == 2
