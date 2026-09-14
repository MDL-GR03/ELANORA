"""Durable event enqueueing and dispatch for external side effects."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.outbox_crypto import EncryptedPayload, OutboxKeyRing
from app.core.settings import get_settings
from app.model.audit_event import OutboxEvent
from app.service.email import EmailService

logger = get_logger()

EXISTING_USER_INVITATION_EMAIL = "invitation.existing_user_email.requested"
ACCOUNT_VERIFICATION_EMAIL = "account.verification_email.requested"
PASSWORD_RESET_EMAIL = "account.password_reset_email.requested"  # noqa: S105
MAX_DELIVERY_ATTEMPTS = 10
SUPPORTED_EVENT_TYPES = (
    EXISTING_USER_INVITATION_EMAIL,
    ACCOUNT_VERIFICATION_EMAIL,
    PASSWORD_RESET_EMAIL,
)


class DispatchResult(StrEnum):
    """Outcome of one attempt to dispatch an outbox record."""

    EMPTY = "empty"
    PUBLISHED = "published"
    FAILED = "failed"


class InvitationEmailSender(Protocol):
    """Port used by the outbox dispatcher for invitation delivery."""

    async def send_existing_user_invitation_email(
        self,
        email: str,
        invitation_id: int,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool: ...

    async def send_email_verification_code(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool: ...

    async def send_password_reset_verification_email(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool: ...


async def enqueue_existing_user_invitation_email(
    db: AsyncSession,
    *,
    invitation_id: int,
    email: str,
    sender_name: str,
    project_name: str,
    custom_message: str | None,
    language: str,
) -> OutboxEvent:
    """Record an email request in the caller's current transaction."""
    event = OutboxEvent(
        aggregate_type="invitation",
        aggregate_id=str(invitation_id),
        event_type=EXISTING_USER_INVITATION_EMAIL,
        payload={
            "invitation_id": invitation_id,
            "email": email,
            "sender_name": sender_name,
            "project_name": project_name,
            "custom_message": custom_message,
            "language": language,
        },
    )
    db.add(event)
    await db.flush()
    return event


async def enqueue_account_verification_email(
    db: AsyncSession,
    *,
    user_id: int,
    email: str,
    username: str,
    code: str,
    language: str,
) -> OutboxEvent:
    """Queue an encrypted account-verification email in the current transaction."""
    return await _enqueue_encrypted_account_email(
        db,
        event_type=ACCOUNT_VERIFICATION_EMAIL,
        user_id=user_id,
        email=email,
        username=username,
        code=code,
        language=language,
    )


async def enqueue_password_reset_email(
    db: AsyncSession,
    *,
    user_id: int,
    email: str,
    username: str,
    code: str,
    language: str,
) -> OutboxEvent:
    """Queue an encrypted password-reset email in the current transaction."""
    return await _enqueue_encrypted_account_email(
        db,
        event_type=PASSWORD_RESET_EMAIL,
        user_id=user_id,
        email=email,
        username=username,
        code=code,
        language=language,
    )


async def _enqueue_encrypted_account_email(
    db: AsyncSession,
    *,
    event_type: str,
    user_id: int,
    email: str,
    username: str,
    code: str,
    language: str,
) -> OutboxEvent:
    key_ring = OutboxKeyRing(get_settings().outbox_encryption_keys.get_secret_value())
    encrypted = key_ring.encrypt(
        {
            "email": email,
            "username": username,
            "code": code,
            "language": language,
        }
    )
    event = OutboxEvent(
        aggregate_type="user",
        aggregate_id=str(user_id),
        event_type=event_type,
        payload={"key_id": encrypted.key_id, "ciphertext": encrypted.ciphertext},
    )
    db.add(event)
    await db.flush()
    return event


class OutboxDispatcher:
    """Publish pending events with PostgreSQL locking and at-least-once delivery."""

    def __init__(
        self,
        email_sender: InvitationEmailSender | None = None,
        key_ring: OutboxKeyRing | None = None,
    ) -> None:
        self.email_sender = email_sender or EmailService()
        self.key_ring = key_ring or OutboxKeyRing(
            get_settings().outbox_encryption_keys.get_secret_value()
        )

    async def dispatch_one(self, db: AsyncSession) -> DispatchResult:
        """Claim and publish the oldest supported event, if one exists."""
        event = await db.scalar(
            select(OutboxEvent)
            .where(
                OutboxEvent.published_at.is_(None),
                OutboxEvent.attempts < MAX_DELIVERY_ATTEMPTS,
                OutboxEvent.event_type.in_(SUPPORTED_EVENT_TYPES),
            )
            .order_by(OutboxEvent.occurred_at, OutboxEvent.event_id)
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        if event is None:
            await db.rollback()
            return DispatchResult.EMPTY

        event.attempts += 1
        try:
            delivered = await self._deliver(event)
            if not delivered:
                raise RuntimeError("email provider did not confirm delivery")
        except Exception as error:
            await db.commit()
            logger.warning(
                "Outbox delivery failed",
                extra={
                    "event_id": str(event.event_id),
                    "event_type": event.event_type,
                    "attempts": event.attempts,
                    "error_type": safe_exception_type(error),
                },
            )
            return DispatchResult.FAILED

        event.published_at = datetime.now(UTC)
        event.payload = {}  # Minimize retained email addresses and personal messages.
        await db.commit()
        logger.info(
            "Outbox event published",
            extra={"event_id": str(event.event_id), "event_type": event.event_type},
        )
        return DispatchResult.PUBLISHED

    async def _deliver(self, event: OutboxEvent) -> bool:
        payload = event.payload
        if event.event_type == EXISTING_USER_INVITATION_EMAIL:
            return await self.email_sender.send_existing_user_invitation_email(
                email=cast("str", payload["email"]),
                invitation_id=int(cast("int", payload["invitation_id"])),
                sender_name=cast("str", payload["sender_name"]),
                project_name=cast("str", payload["project_name"]),
                custom_message=cast("str | None", payload.get("custom_message")),
                language=cast("str", payload["language"]),
            )

        decrypted = self.key_ring.decrypt(
            EncryptedPayload(
                key_id=cast("str", payload["key_id"]),
                ciphertext=cast("str", payload["ciphertext"]),
            )
        )
        common = {
            "email": cast("str", decrypted["email"]),
            "username": cast("str", decrypted["username"]),
            "code": cast("str", decrypted["code"]),
            "language": cast("str", decrypted["language"]),
        }
        if event.event_type == ACCOUNT_VERIFICATION_EMAIL:
            return await self.email_sender.send_email_verification_code(**common)
        if event.event_type == PASSWORD_RESET_EMAIL:
            return await self.email_sender.send_password_reset_verification_email(
                **common
            )
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")

    async def dispatch_pending(self, db: AsyncSession, limit: int = 100) -> int:
        """Dispatch up to ``limit`` events and return the successful count."""
        published = 0
        for _ in range(limit):
            result = await self.dispatch_one(db)
            if result == DispatchResult.EMPTY:
                break
            if result == DispatchResult.FAILED:
                break  # Avoid hammering the same oldest event in a tight loop.
            if result == DispatchResult.PUBLISHED:
                published += 1
        return published
