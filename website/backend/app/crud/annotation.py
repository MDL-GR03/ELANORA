"""Annotation CRUD operations - Pure database access layer."""

from decimal import Decimal

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.elan.persistence import PersistedTier
from app.model.annotation import Annotation
from app.model.annotation_value import AnnotationValue
from app.utils.database import DatabaseUtils

logger = get_logger()


async def delete_unused_annotation_values(db: AsyncSession) -> int:
    """Delete annotation values not referenced by any annotation."""
    try:
        subquery = select(Annotation.value_id)
        count = await DatabaseUtils.bulk_delete(
            db, AnnotationValue, ~AnnotationValue.value_id.in_(subquery)
        )
        logger.info(f"Deleted {count} unused AnnotationValue rows")
        return count
    except Exception:
        await db.rollback()
        raise


async def get_annotation_by_id(
    db: AsyncSession, annotation_id: str, elan_id: int
) -> Annotation | None:
    """Retrieve an annotation by ID."""
    filters = {"annotation_id": annotation_id, "elan_id": elan_id}
    return await DatabaseUtils.get_one_by_filter(db, Annotation, filters)


async def get_annotations_by_tier(db: AsyncSession, tier_id: int) -> list[Annotation]:
    """Get all annotations for a specific tier."""
    filters = {"tier_id": tier_id}
    order_by = [Annotation.start_time]
    return await DatabaseUtils.get_by_filter(db, Annotation, filters, order_by=order_by)


async def get_annotations_with_value_by_tier(
    db: AsyncSession, tier_id: int
) -> list[Annotation]:
    """Get all annotations with their values for a specific tier.

    Args:
        db: Database session.
        tier_id: The tier ID to filter by.

    Returns:
        List of annotations with their values for the tier, ordered by start time.

    """
    result = await db.execute(
        select(Annotation)
        .options(selectinload(Annotation.annotation_value))
        .filter(Annotation.tier_id == tier_id)
        .order_by(Annotation.start_time)
    )
    return list(result.scalars().all())


async def get_annotations_by_time_range(
    db: AsyncSession, tier_id: int, start_time: Decimal, end_time: Decimal
) -> list[Annotation]:
    """Get annotations within a time range for a specific tier."""
    result = await db.execute(
        select(Annotation)
        .filter(
            and_(
                Annotation.tier_id == tier_id,
                Annotation.start_time >= start_time,
                Annotation.end_time <= end_time,
            )
        )
        .order_by(Annotation.start_time)
    )
    return list(result.scalars().all())


async def create_annotation_in_db(
    db: AsyncSession,
    annotation_id: str,
    elan_id: int,
    value_id: int,
    start_time: Decimal | None,
    end_time: Decimal | None,
    tier_id: int,
    annotation_kind: str = "alignable",
) -> Annotation:
    """Create a new annotation in the database."""
    annotation = Annotation(
        annotation_id=annotation_id,
        elan_id=elan_id,
        value_id=value_id,
        annotation_kind=annotation_kind,
        start_time=start_time,
        end_time=end_time,
        tier_id=tier_id,
    )
    return await DatabaseUtils.create(db, annotation)


async def check_annotation_exists(
    db: AsyncSession, annotation_id: str, elan_id: int
) -> bool:
    return await get_annotation_by_id(db, annotation_id, elan_id) is not None


async def delete_annotations_by_tier(db: AsyncSession, tier_id: int) -> int:
    """Delete all annotations for a tier."""
    try:
        count = await DatabaseUtils.bulk_delete(
            db, Annotation, Annotation.tier_id == tier_id
        )
        await delete_unused_annotation_values(db)
        return count
    except Exception:
        await db.rollback()
        raise


async def bulk_create_annotations(
    db: AsyncSession,
    tiers_data: list[PersistedTier],
    elan_id: int,
    value_map: dict[str, int],
) -> None:
    """Bulk create annotations for multiple tiers."""
    all_annotations = []
    for tier_data in tiers_data:
        tier_id = tier_data["tier_id"]
        for ann in tier_data["annotations"]:
            all_annotations.append(
                {
                    "annotation_id": ann["annotation_id"],
                    "elan_id": elan_id,
                    "value_id": value_map[ann["annotation_value"]],
                    "annotation_kind": ann["annotation_kind"],
                    "annotation_ref": ann.get("annotation_ref"),
                    "previous_annotation": ann.get("previous_annotation"),
                    "cv_entry_ref": ann.get("cv_entry_ref"),
                    "external_ref": ann.get("ext_ref"),
                    "start_time": ann["start_time"],
                    "end_time": ann["end_time"],
                    "tier_id": tier_id,
                }
            )
    if all_annotations:
        await DatabaseUtils.bulk_insert(db, Annotation, all_annotations)


async def delete_annotations_by_file(db: AsyncSession, elan_id: int) -> int:
    """Delete all annotations for a given ELAN file."""
    try:
        count = await DatabaseUtils.bulk_delete(
            db, Annotation, Annotation.elan_id == elan_id
        )
        await delete_unused_annotation_values(db)
        await db.flush()
        return count
    except Exception as e:
        logger.error(
            "Failed to delete annotations by file; error_type=%s",
            safe_exception_type(e),
        )
        raise
