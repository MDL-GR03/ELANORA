"""Persistence operations for immutable EAF source revisions."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.eaf_revision import EafRevision


async def append_eaf_revision(
    db: AsyncSession,
    *,
    elan_id: int,
    sha256: str,
    raw_xml: bytes,
    created_by: int | None,
) -> EafRevision:
    """Append a new revision or return the existing identical revision."""
    existing = (
        await db.execute(
            select(EafRevision).where(
                EafRevision.elan_id == elan_id, EafRevision.sha256 == sha256
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    next_number = (
        await db.execute(
            select(func.coalesce(func.max(EafRevision.revision_number), 0) + 1).where(
                EafRevision.elan_id == elan_id
            )
        )
    ).scalar_one()
    revision = EafRevision(
        elan_id=elan_id,
        revision_number=next_number,
        sha256=sha256,
        raw_xml=raw_xml,
        created_by=created_by,
    )
    db.add(revision)
    await db.flush()
    return revision
