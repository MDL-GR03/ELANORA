"""Durable storage boundary for institution assets."""

import uuid
from pathlib import Path
from typing import Any, Protocol, cast

import boto3  # type: ignore[import-untyped]

from app.core.settings import get_settings


class AssetStorage(Protocol):
    def put(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self, prefix: str) -> list[str]: ...


class LocalAssetStorage:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def put(self, key: str, content: bytes) -> None:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Asset key escapes storage root")
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f".{target.name}.{uuid.uuid4().hex}.tmp")
        try:
            temporary.write_bytes(content)
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)

    def read(self, key: str) -> bytes:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Asset key escapes storage root")
        return target.read_bytes()

    def list_keys(self, prefix: str) -> list[str]:
        scope = (self.root / prefix).resolve()
        if scope != self.root and self.root not in scope.parents:
            raise ValueError("Asset key escapes storage root")
        return sorted(
            str(path.relative_to(self.root))
            for path in self.root.rglob("*")
            if path.is_file() and str(path.relative_to(self.root)).startswith(prefix)
        )

    def delete(self, key: str) -> None:
        target = (self.root / key).resolve()
        if self.root not in target.parents:
            raise ValueError("Asset key escapes storage root")
        target.unlink(missing_ok=True)
        parent = target.parent
        while parent != self.root:
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


class S3AssetStorage:
    """Store immutable-key assets in an S3-compatible object store."""

    def __init__(
        self,
        bucket: str,
        *,
        prefix: str = "elanora",
        client: Any | None = None,
        region: str | None = None,
        endpoint_url: str | None = None,
        access_key_id: str | None = None,
        secret_access_key: str | None = None,
    ) -> None:
        if not bucket.strip():
            raise ValueError("Asset bucket must not be empty")
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self.client = client or boto3.client(
            "s3",
            region_name=region,
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key_id,
            aws_secret_access_key=secret_access_key,
        )

    def _object_key(self, key: str) -> str:
        parts = Path(key).parts
        if (
            not parts
            or Path(key).is_absolute()
            or any(part in {"", ".", ".."} for part in parts)
        ):
            raise ValueError("Invalid asset key")
        normalized = "/".join(parts)
        return f"{self.prefix}/{normalized}" if self.prefix else normalized

    def put(self, key: str, content: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
            Body=content,
            IfNoneMatch="*",
        )

    def read(self, key: str) -> bytes:
        response = self.client.get_object(
            Bucket=self.bucket,
            Key=self._object_key(key),
        )
        return cast("bytes", response["Body"].read())

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._object_key(key))

    def list_keys(self, prefix: str) -> list[str]:
        """Keys under a prefix, without the store-wide prefix, in one listing."""
        scope = f"{self.prefix}/{prefix}" if self.prefix else prefix
        paginator = self.client.get_paginator("list_objects_v2")
        keys: list[str] = []
        for page in paginator.paginate(Bucket=self.bucket, Prefix=scope):
            for item in page.get("Contents", []):
                key = str(item["Key"])
                keys.append(key[len(self.prefix) + 1 :] if self.prefix else key)
        return sorted(keys)


def get_asset_storage() -> AssetStorage:
    """Resolve the configured asset backend behind a stable domain boundary."""
    settings = get_settings()
    if settings.asset_storage_backend == "s3":
        return S3AssetStorage(
            settings.asset_s3_bucket or "",
            prefix=settings.asset_s3_prefix,
            region=settings.asset_s3_region,
            endpoint_url=settings.asset_s3_endpoint_url,
            access_key_id=(
                settings.asset_s3_access_key_id.get_secret_value()
                if settings.asset_s3_access_key_id
                else None
            ),
            secret_access_key=(
                settings.asset_s3_secret_access_key.get_secret_value()
                if settings.asset_s3_secret_access_key
                else None
            ),
        )
    return LocalAssetStorage(settings.instance_assets_base_path)


def get_backup_storage() -> AssetStorage:
    """Resolve where nightly backups are written, off this host in production."""
    settings = get_settings()
    if settings.backup_storage_backend == "s3":
        return S3AssetStorage(
            settings.backup_s3_bucket or "",
            prefix=settings.backup_s3_prefix,
            region=settings.backup_s3_region,
            endpoint_url=settings.backup_s3_endpoint_url,
            access_key_id=(
                settings.backup_s3_access_key_id.get_secret_value()
                if settings.backup_s3_access_key_id
                else None
            ),
            secret_access_key=(
                settings.backup_s3_secret_access_key.get_secret_value()
                if settings.backup_s3_secret_access_key
                else None
            ),
        )
    return LocalAssetStorage(Path(settings.backup_local_root))
