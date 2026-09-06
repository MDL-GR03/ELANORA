import io

import pytest
from PIL import Image
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import BootstrapConfig, bootstrap
from app.model.audit_event import AuditEvent
from app.service import instance_assets
from app.storage.assets import LocalAssetStorage


@pytest.mark.asyncio
async def test_logo_is_persisted_linked_and_audited(
    session: AsyncSession, tmp_path, monkeypatch
) -> None:
    config = BootstrapConfig(
        instance_name="Portal",
        institution_name="Research Institute",
        contact_email="research@example.org",
        domain="example.org",
        timezone="Europe/Paris",
        default_language="en",
        admin_username="owner",
        admin_email="owner@example.org",
        admin_first_name="Research",
        admin_last_name="Owner",
        admin_affiliation="Research Institute",
        admin_department="Corpus Lab",
    )
    instance, owner = await bootstrap(session, config, "correct horse battery staple")
    monkeypatch.setattr(
        instance_assets, "get_asset_storage", lambda: LocalAssetStorage(tmp_path)
    )
    source = io.BytesIO()
    Image.new("RGBA", (300, 120), "#2563eb").save(source, format="PNG")

    asset = await instance_assets.replace_logo(
        session, instance, owner, source.getvalue()
    )

    assert instance.logo_asset_id == asset.asset_id
    assert await instance_assets.read_logo(session, instance) is not None
    event = await session.scalar(
        select(AuditEvent).where(AuditEvent.action == "instance.logo.replaced")
    )
    assert event is not None
    assert event.details["asset_id"] == str(asset.asset_id)
