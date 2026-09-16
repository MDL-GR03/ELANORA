"""Annotation CRUD operations - Pure database access layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
