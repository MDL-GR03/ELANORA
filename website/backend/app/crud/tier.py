"""Tier CRUD operations - Pure database access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.model.annotation import Annotation
from app.model.association import ElanFileToTier
from app.model.tier import Tier
from app.utils.database import DatabaseUtils

logger = get_logger()


async def delete_tiers_for_elan_file(db: AsyncSession, elan_id: int) -> None:
    logger.info(f"Bulk deleting tiers and annotations for elan_id={elan_id}")
    try:
        tier_ids = list(
            (await db.execute(select(Tier.tier_id).where(Tier.elan_id == elan_id)))
            .scalars()
            .all()
        )
        logger.info(f"tier_ids to delete for elan_id={elan_id}: {tier_ids}")
        if tier_ids:
            await DatabaseUtils.bulk_delete(
                db, Annotation, Annotation.tier_id.in_(tier_ids)
            )
            await DatabaseUtils.bulk_delete(
                db,
                ElanFileToTier,
                (ElanFileToTier.elan_id == elan_id)
                & ElanFileToTier.tier_id.in_(tier_ids),
            )
            await DatabaseUtils.bulk_delete(db, Tier, Tier.elan_id == elan_id)
        logger.info(f"Bulk deleted tiers and annotations for elan_id={elan_id}")
    except Exception as e:
        logger.error(
            "Failed to bulk delete ELAN tiers; error_type=%s",
            safe_exception_type(e),
        )
        raise


async def get_tier_by_name(
    db: AsyncSession, tier_name: str, elan_id: int
) -> Tier | None:
    filters = {"tier_name": tier_name, "elan_id": elan_id}
    return await DatabaseUtils.get_one_by_filter(db, Tier, filters)


async def create_tier_in_db(
    db: AsyncSession,
    tier_name: str,
    elan_id: int,
    linguistic_type_ref: str,
    eaf_attributes: dict[str, str] | None = None,
    parent_tier_id: int | None = None,
) -> Tier:
    """Create a new tier in the database."""
    tier = Tier(
        tier_name=tier_name,
        elan_id=elan_id,
        linguistic_type_ref=linguistic_type_ref,
        eaf_attributes=eaf_attributes or {},
        parent_tier_id=parent_tier_id,
    )
    await DatabaseUtils.create(db, tier)
    await db.flush()
    return tier


async def get_tiers_by_elan_id(db: AsyncSession, elan_id: int) -> list[Tier]:
    """Get all tiers for a given ELAN file."""
    result = await db.execute(select(Tier).where(Tier.elan_id == elan_id))
    return list(result.scalars().all())


async def update_parent_tier(
    db: AsyncSession, tier_id: int, parent_tier_id: int
) -> None:
    """Update the parent_tier_id for a tier."""
    filters = {"tier_id": tier_id}
    update_fields = {"parent_tier_id": parent_tier_id}
    await DatabaseUtils.update_by_filter(db, Tier, filters, update_fields)
    await db.flush()
