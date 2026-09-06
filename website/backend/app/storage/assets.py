"""Durable storage boundary for institution assets."""

from pathlib import Path
from typing import Protocol

from app.core.settings import get_settings


class AssetStorage(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...


class LocalAssetStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, key: str, content: bytes) -> None:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Asset key escapes storage root")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_suffix(".tmp")
        temporary.write_bytes(content)
        temporary.replace(target)

    def read(self, key: str) -> bytes:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Asset key escapes storage root")
        return target.read_bytes()


def get_asset_storage() -> AssetStorage:
    """Resolve the configured asset backend behind a stable domain boundary."""
    return LocalAssetStorage(get_settings().instance_assets_base_path)
