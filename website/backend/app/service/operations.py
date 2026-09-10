"""Administrator-safe operational health reporting."""

import secrets
from datetime import UTC, datetime
from urllib.parse import urlparse

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import Settings, get_settings
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.schema.responses.operations import (
    IntegrityStatusResponse,
    OperationsStatusResponse,
    RecoveryStatusResponse,
    StorageCheckResponse,
    StorageStatusResponse,
)
from app.storage.assets import AssetStorage, get_asset_storage

MINIMUM_MASKABLE_BUCKET_LENGTH = 4


def _masked_bucket(bucket: str | None) -> str:
    if not bucket:
        return "—"
    if len(bucket) <= MINIMUM_MASKABLE_BUCKET_LENGTH:
        return "••••"
    return f"{bucket[:2]}...{bucket[-2:]}"


def storage_status(settings: Settings) -> StorageStatusResponse:
    if settings.asset_storage_backend == "s3":
        endpoint = urlparse(settings.asset_s3_endpoint_url or "").hostname
        destination = _masked_bucket(settings.asset_s3_bucket)
        if endpoint:
            destination = f"{destination} via {endpoint}"
        credentials = (
            "static_deployment_secret"
            if settings.asset_s3_access_key_id
            else "workload_identity"
        )
        policy = "external_object_storage_controls"
    else:
        destination = "local_filesystem"
        credentials = "operating_system_permissions"
        policy = "encrypted_recovery_bundle"
    return StorageStatusResponse(
        backend=settings.asset_storage_backend,
        location_hint=destination,
        credentials_source=credentials,
        policy_verification=policy,
    )


async def operations_status(db: AsyncSession) -> OperationsStatusResponse:
    total_projects = int(await db.scalar(select(func.count(Project.project_id))) or 0)
    row = (
        await db.execute(
            select(
                func.count(ProjectIntegrityStatus.project_id),
                func.count(case((ProjectIntegrityStatus.status == "healthy", 1))),
                func.max(ProjectIntegrityStatus.last_checked_at),
            )
        )
    ).one()
    tracked = int(row[0] or 0)
    healthy = int(row[1] or 0)
    return OperationsStatusResponse(
        storage=storage_status(get_settings()),
        integrity=IntegrityStatusResponse(
            total_projects=total_projects,
            scanned_projects=tracked,
            healthy_projects=healthy,
            unhealthy_projects=tracked - healthy,
            unscanned_projects=max(total_projects - tracked, 0),
            latest_check_at=row[2],
        ),
        recovery=RecoveryStatusResponse(
            responsibility="deployment_operator",
            latest_drill_at=None,
            state="not_reported",
        ),
    )


def check_storage(storage: AssetStorage | None = None) -> StorageCheckResponse:
    backend = storage or get_asset_storage()
    key = f"operations/probes/{secrets.token_hex(16)}"
    content = secrets.token_bytes(32)
    try:
        backend.put(key, content)
        restored = backend.read(key)
        if not secrets.compare_digest(content, restored):
            raise RuntimeError("Storage returned different bytes")
    finally:
        backend.delete(key)
    return StorageCheckResponse(status="healthy", checked_at=datetime.now(UTC))
