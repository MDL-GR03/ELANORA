from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.model.component_accepted_value import ComponentAcceptedValue
from app.model.component_template import ComponentTemplate
from app.model.standard_component import StandardComponent
from app.utils.database import DatabaseUtils

logger = get_logger(__name__)


async def link_component_to_accepted_value(
    db: AsyncSession, component_template_id: int, accepted_value_id: int
):
    filters = {
        "component_template_id": component_template_id,
        "accepted_value_id": accepted_value_id,
    }
    link = await DatabaseUtils.get_one_by_filter(db, ComponentAcceptedValue, filters)
    if not link:
        link = ComponentAcceptedValue(
            component_template_id=component_template_id,
            accepted_value_id=accepted_value_id,
        )
        await DatabaseUtils.create(db, link)
        await db.flush()
    return link


async def unlink_component_from_accepted_value(
    db: AsyncSession, component_template_id: int, accepted_value_id: int
):
    return await DatabaseUtils.delete_by_filter(
        db,
        ComponentAcceptedValue,
        component_template_id=component_template_id,
        accepted_value_id=accepted_value_id,
    )


async def delete_for_orphaned_templates(db: AsyncSession):
    try:
        logger.info(
            "Starting orphaned ComponentAcceptedValue cleanup for orphaned templates..."
        )
        referenced_ids_result = await db.execute(
            select(StandardComponent.component_template_id)
        )
        referenced_ids = {row[0] for row in referenced_ids_result}
        orphaned_templates_result = await db.execute(
            select(ComponentTemplate.id).where(
                ~ComponentTemplate.id.in_(referenced_ids)
            )
        )
        orphaned_template_ids = [row[0] for row in orphaned_templates_result]
        logger.info(f"Orphaned template IDs: {orphaned_template_ids}")
        if orphaned_template_ids:
            deleted = await DatabaseUtils.bulk_delete(
                db,
                ComponentAcceptedValue,
                ComponentAcceptedValue.component_template_id.in_(orphaned_template_ids),
            )
            logger.info(
                f"Deleted {deleted} ComponentAcceptedValue rows for orphaned templates."
            )
            await db.flush()
        else:
            logger.info(
                "No orphaned templates found for ComponentAcceptedValue cleanup."
            )
    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to delete orphaned component values; error_type=%s",
            safe_exception_type(e),
        )
        raise
