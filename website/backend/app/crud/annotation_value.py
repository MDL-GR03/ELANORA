from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.elan.persistence import PersistedTier
from app.model.annotation_value import AnnotationValue
from app.utils.database import DatabaseUtils

logger = get_logger()


async def bulk_get_or_create_annotation_values(
    db: AsyncSession, tiers_data: list[PersistedTier]
) -> dict[str, int]:
    """Bulk get or create annotation values, returning a mapping from value to ID."""
    all_ann_values = {
        ann["annotation_value"]
        for tier_data in tiers_data
        for ann in tier_data["annotations"]
    }
    value_map = {}
    logger.info("Processing %s unique annotation values", len(all_ann_values))
    if all_ann_values:
        # Fetch existing values using DatabaseUtils
        filters = {"annotation_value": list(all_ann_values)}
        existing_values = await DatabaseUtils.get_by_filter(
            db, AnnotationValue, filters
        )
        for obj in existing_values:
            value_map[obj.annotation_value] = obj.value_id
        missing_values = [v for v in all_ann_values if v not in value_map]
        logger.info(
            f"Existing values in DB: {len(value_map)}. Missing: {len(missing_values)}"
        )
        if missing_values:
            # Bulk insert missing values using DatabaseUtils
            await DatabaseUtils.bulk_insert(
                db,
                AnnotationValue,
                [{"annotation_value": v} for v in missing_values],
                ignore_duplicates=True,
            )
            await db.flush()
            logger.info(f"Inserted or ignored {len(missing_values)} values.")
            # Fetch all values again to update the map
            filters = {"annotation_value": list(missing_values)}
            new_values = await DatabaseUtils.get_by_filter(db, AnnotationValue, filters)
            for obj in new_values:
                value_map[obj.annotation_value] = obj.value_id
    logger.info(f"Completed. Returning value_map with {len(value_map)} entries.")
    return value_map
