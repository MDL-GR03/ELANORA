from collections.abc import AsyncIterator
from datetime import UTC

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import BootstrapConfig, bootstrap
from app.core.settings import DEVELOPMENT_SETUP_TOKEN
from app.db.database import get_db
from app.main import app
from app.model.enums import UserRole
from app.model.user import User
from app.service import user_sessions
from app.utils import password_hashing


@pytest.mark.asyncio
async def test_bootstrap_creates_one_verified_tenant_admin_atomically(
    session: AsyncSession,
) -> None:
    config = BootstrapConfig(
        instance_name="Portal",
        institution_name="Research Institute",
        contact_email="research@example.org",
        domain="example.org",
        timezone="Europe/Paris",
        default_language="en",
        admin_username="administrator",
        admin_email="administrator@example.org",
        admin_first_name="Platform",
        admin_last_name="Administrator",
        admin_affiliation="Research Institute",
        admin_department="Research IT",
    )

    instance, user = await bootstrap(session, config, "correct horse battery staple")

    assert user.instance_id == instance.instance_id
    assert instance.installation_id is not None
    assert instance.primary_color == "#2563eb"
    assert user.role == UserRole.ADMIN
    assert user.is_verified_account is True
    assert password_hashing.verify_password(
        "correct horse battery staple", user.hashed_password
    )
    with pytest.raises(RuntimeError, match="already exists"):
        await bootstrap(session, config, "another secure password")


@pytest.mark.asyncio
async def test_successful_login_records_timezone_aware_timestamp(
    session: AsyncSession,
) -> None:
    config = BootstrapConfig(
        instance_name="Portal",
        institution_name="Research Institute",
        contact_email="research@example.org",
        domain="example.org",
        timezone="Europe/Paris",
        default_language="en",
        admin_username="administrator",
        admin_email="administrator@example.org",
        admin_first_name="Platform",
        admin_last_name="Administrator",
        admin_affiliation="Research Institute",
        admin_department="Research IT",
    )
    _, user = await bootstrap(session, config, "correct horse battery staple")

    result = await user_sessions.login_user(
        session,
        "administrator",
        "correct horse battery staple",
    )

    assert result.needs_verification is False
    assert user.last_login is not None
    assert user.last_login.tzinfo is UTC
    assert User.__table__.c.last_login.type.timezone is True


@pytest.mark.asyncio
async def test_browser_setup_is_token_guarded_atomic_and_one_time(
    session: AsyncSession,
) -> None:
    async def override_database() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_db] = override_database
    payload = {
        "instance_name": "Signs Lab",
        "institution_name": "Language Research Institute",
        "contact_email": "contact@example.org",
        "domain": "example.org",
        "timezone": "Europe/Paris",
        "default_language": "en",
        "primary_color": "#234e70",
        "secondary_color": "#0f766e",
        "accent_color": "#b45309",
        "admin_username": "owner",
        "admin_email": "owner@example.org",
        "admin_first_name": "Research",
        "admin_last_name": "Owner",
        "admin_affiliation": "Language Research Institute",
        "admin_department": "Corpus Lab",
        "password": "correct horse battery staple",
        "password_confirmation": "correct horse battery staple",
    }
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://localhost"
        ) as client:
            status_response = await client.get("/api/v1/setup/status")
            assert status_response.json()["initialized"] is False

            denied = await client.post(
                "/api/v1/setup/initialize",
                json=payload,
                headers={"X-ELANORA-Setup-Token": "incorrect-token"},
            )
            assert denied.status_code == 403

            created = await client.post(
                "/api/v1/setup/initialize",
                json=payload,
                headers={"X-ELANORA-Setup-Token": DEVELOPMENT_SETUP_TOKEN},
            )
            assert created.status_code == 201
            assert created.json()["instance"]["primary_color"] == "#234e70"
            assert created.json()["administrator_username"] == "owner"

            repeated = await client.post(
                "/api/v1/setup/initialize",
                json=payload,
                headers={"X-ELANORA-Setup-Token": DEVELOPMENT_SETUP_TOKEN},
            )
            assert repeated.status_code == 409
    finally:
        app.dependency_overrides.clear()
