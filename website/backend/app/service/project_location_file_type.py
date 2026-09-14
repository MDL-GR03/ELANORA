from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project_location_file_type import (
    add_file_type_to_location,
    get_file_types_for_location,
    remove_file_type_from_location,
)
from app.model.project_location_file_type import ProjectLocationFileType


async def service_add_file_type_to_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
) -> ProjectLocationFileType:
    try:
        instance = await add_file_type_to_location(
            db, project_id, location_id, project_file_type_id
        )
        await db.commit()
        return instance
    except Exception:
        await db.rollback()
        raise


async def service_remove_file_type_from_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
) -> int:
    try:
        count = await remove_file_type_from_location(
            db, project_id, location_id, project_file_type_id
        )
        await db.commit()
        return count
    except Exception:
        await db.rollback()
        raise


async def service_get_file_types_for_location(
    db: AsyncSession, project_id: int, location_id: int
) -> list[ProjectLocationFileType]:
    return await get_file_types_for_location(db, project_id, location_id)
