"""Reading the protocol a project is pinned to, and hashing rules."""

import hashlib
import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.enums import (
    ProtocolVersionStatus,
)
from app.model.project import Project
from app.model.protocol import (
    Protocol,
    ProtocolVersion,
)
from app.schema.protocol import (
    ProtocolRules,
)
from app.service.protocol_errors import (
    ProtocolConflictError,
    ProtocolNotFoundError,
)

FULL_COVERAGE_PERCENT = 100.0


async def get_pinned_protocol_version(
    db: AsyncSession, project: Project
) -> ProtocolVersion | None:
    """Resolve the project's published immutable protocol snapshot, if configured."""
    if project.protocol_version_id is None:
        return None
    version = await db.scalar(
        select(ProtocolVersion).where(
            ProtocolVersion.protocol_version_id == project.protocol_version_id,
            ProtocolVersion.status == ProtocolVersionStatus.PUBLISHED,
        )
    )
    if version is None:
        raise ProtocolConflictError(
            "The project's pinned protocol is unavailable or unpublished"
        )
    return version


def _rules_dict(rules: ProtocolRules) -> dict[str, object]:
    return rules.model_dump(mode="json")


def _rules_checksum(rules: dict[str, object]) -> str:
    canonical = json.dumps(
        rules, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def _scoped_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    lock: bool = False,
) -> ProtocolVersion:
    statement = (
        select(ProtocolVersion)
        .join(Protocol, Protocol.protocol_id == ProtocolVersion.protocol_id)
        .where(
            ProtocolVersion.protocol_version_id == protocol_version_id,
            Protocol.instance_id == project.instance_id,
        )
        .options(selectinload(ProtocolVersion.archive))
    )
    if lock:
        statement = statement.with_for_update()
    version = await db.scalar(statement)
    if version is None:
        raise ProtocolNotFoundError("Protocol version not found")
    return version
