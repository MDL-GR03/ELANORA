from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.model.accepted_value import AcceptedValue
from app.model.component_accepted_value import ComponentAcceptedValue
from app.utils.database import DatabaseUtils

logger = get_logger(__name__)


async def get_or_create_accepted_value(db: AsyncSession, value: str) -> AcceptedValue:
    filters = {"value": value}
    obj = await DatabaseUtils.get_one_by_filter(db, AcceptedValue, filters)
    if obj:
        return obj
    obj = AcceptedValue(value=value)
    await DatabaseUtils.create(db, obj)
    await db.flush()
    return obj


async def delete_orphaned_accepted_values(db: AsyncSession) -> int:
    try:
        logger.info("Starting orphaned AcceptedValue cleanup...")
        # Count before
        before = (
            await db.execute(select(func.count()).select_from(AcceptedValue))
        ).scalar()
        logger.info(f"AcceptedValue rows before cleanup: {before}")
        # Delete orphans
        result = await DatabaseUtils.delete_fully_orphaned(
            db, AcceptedValue, ComponentAcceptedValue, "id", "accepted_value_id"
        )
        # Count after
        after = (
            await db.execute(select(func.count()).select_from(AcceptedValue))
        ).scalar()
        logger.info(f"AcceptedValue rows after cleanup: {after}")
        await db.flush()
        return result
    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to delete orphaned accepted values; error_type=%s",
            safe_exception_type(e),
        )
        raise
