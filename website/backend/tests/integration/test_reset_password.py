"""Administrative password recovery tests."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import BootstrapConfig, bootstrap
from app.cli.reset_password import reset_password
from app.service.user import UserService


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
    _, original = await bootstrap(session, config, "old-password-123")

    updated = await reset_password(session, "administrator", "new-password-456")

    assert updated.user_id == original.user_id
    assert UserService.verify_password("new-password-456", updated.hashed_password)
    assert not UserService.verify_password("old-password-123", updated.hashed_password)
