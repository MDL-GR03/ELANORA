"""API-level tests for encrypted account email delivery requests."""

from collections.abc import AsyncIterator

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import router as auth_router
from app.core.outbox_crypto import EncryptedPayload, OutboxKeyRing
from app.core.settings import get_settings
from app.db.database import get_db
from app.model.audit_event import OutboxEvent
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.user import User
from app.service.outbox import ACCOUNT_VERIFICATION_EMAIL, PASSWORD_RESET_EMAIL

api_app = FastAPI()
api_app.include_router(auth_router, prefix="/api/v1/auth")


def _user(institution: Instance) -> User:
    return User(
        username="researcher",
        email="researcher@example.org",
        hashed_password="unused-test-value",  # noqa: S106 - inert fixture
        first_name="Ada",
        last_name="Researcher",
        affiliation="Research Institute",
        department="Sign Linguistics",
        activation_code="initial",
        is_verified_account=False,
        instance=institution,
        role=UserRole.PUBLIC,
    )


async def _client(session: AsyncSession) -> AsyncIterator[AsyncClient]:
    async def override_database() -> AsyncIterator[AsyncSession]:
        yield session

    api_app.dependency_overrides[get_db] = override_database
    try:
        async with AsyncClient(
            transport=ASGITransport(app=api_app), base_url="http://localhost"
        ) as client:
            yield client
    finally:
        api_app.dependency_overrides.pop(get_db, None)


def _decrypt(event: OutboxEvent) -> dict[str, object]:
    key_ring = OutboxKeyRing(get_settings().outbox_encryption_keys.get_secret_value())
    return key_ring.decrypt(
        EncryptedPayload(
            key_id=str(event.payload["key_id"]),
            ciphertext=str(event.payload["ciphertext"]),
        )
    )


@pytest.mark.asyncio
async def test_forgot_password_queues_encrypted_reset_email(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = _user(institution)
    session.add_all([institution, user])
    await session.commit()

    async for client in _client(session):
        response = await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email, "language": "en"},
        )

    event = await session.scalar(select(OutboxEvent))
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert event is not None
    assert event.event_type == PASSWORD_RESET_EMAIL
    assert user.email not in str(event.payload)
    decrypted = _decrypt(event)
    assert decrypted["email"] == user.email
    assert str(decrypted["code"]).isdigit()
    assert len(str(decrypted["code"])) == 6


@pytest.mark.asyncio
async def test_verification_resend_queues_encrypted_email(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Institute",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = _user(institution)
    session.add_all([institution, user])
    await session.commit()

    async for client in _client(session):
        response = await client.post(
            "/api/v1/auth/send-verification-email",
            json={"email": user.email, "language": "fr"},
        )

    event = await session.scalar(select(OutboxEvent))
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert event is not None
    assert event.event_type == ACCOUNT_VERIFICATION_EMAIL
    assert user.email not in str(event.payload)
    decrypted = _decrypt(event)
    assert decrypted["email"] == user.email
    assert decrypted["language"] == "fr"
