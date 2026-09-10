from pathlib import Path

from app.core.settings import Settings
from app.service.operations import check_storage, storage_status
from app.storage.assets import LocalAssetStorage


def test_status_never_exposes_s3_credentials() -> None:
    settings = Settings(
        asset_storage_backend="s3",
        asset_s3_bucket="institution-private-assets",
        asset_s3_endpoint_url="https://objects.example.org/private",
        asset_s3_access_key_id="private-access-id",
        asset_s3_secret_access_key="private-secret",  # noqa: S106
    )

    status = storage_status(settings)

    serialized = status.model_dump_json()
    assert status.location_hint == "in...ts via objects.example.org"
    assert "private-access-id" not in serialized
    assert "private-secret" not in serialized


def test_storage_check_round_trips_and_removes_probe(tmp_path: Path) -> None:
    result = check_storage(LocalAssetStorage(tmp_path))

    assert result.status == "healthy"
    assert list(tmp_path.rglob("*")) == []
