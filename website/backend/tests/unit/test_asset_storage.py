import io
from pathlib import Path

import pytest

from app.core.settings import Settings
from app.storage.assets import LocalAssetStorage, S3AssetStorage


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    def put_object(self, **arguments: object) -> None:
        identity = (str(arguments["Bucket"]), str(arguments["Key"]))
        if arguments.get("IfNoneMatch") == "*" and identity in self.objects:
            raise RuntimeError("object already exists")
        self.objects[identity] = bytes(arguments["Body"])

    def get_object(self, **arguments: object) -> dict[str, io.BytesIO]:
        identity = (str(arguments["Bucket"]), str(arguments["Key"]))
        return {"Body": io.BytesIO(self.objects[identity])}


def test_local_storage_round_trip_is_confined_to_root(tmp_path: Path) -> None:
    storage = LocalAssetStorage(tmp_path)
    storage.put("instances/example/logo.webp", b"logo")

    assert storage.read("instances/example/logo.webp") == b"logo"
    with pytest.raises(ValueError, match="escapes storage root"):
        storage.put("../outside", b"forbidden")


def test_s3_storage_uses_prefixed_immutable_keys() -> None:
    client = FakeS3Client()
    storage = S3AssetStorage("assets", prefix="institution", client=client)

    storage.put("instances/example/logo.webp", b"logo")

    assert storage.read("instances/example/logo.webp") == b"logo"
    assert (
        client.objects[("assets", "institution/instances/example/logo.webp")] == b"logo"
    )
    with pytest.raises(RuntimeError, match="already exists"):
        storage.put("instances/example/logo.webp", b"replacement")


@pytest.mark.parametrize("key", ["../outside", "/absolute", "part/../outside"])
def test_s3_storage_rejects_unsafe_keys(key: str) -> None:
    storage = S3AssetStorage("assets", client=FakeS3Client())

    with pytest.raises(ValueError, match="Invalid asset key"):
        storage.read(key)


def test_s3_settings_require_bucket_and_complete_static_credentials() -> None:
    with pytest.raises(ValueError, match="ASSET_S3_BUCKET"):
        Settings(asset_storage_backend="s3")

    with pytest.raises(ValueError, match="must be set together"):
        Settings(asset_s3_access_key_id="access-only")
