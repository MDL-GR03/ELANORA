from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project_location_file_type import (
    add_file_type_to_location,
    get_file_types_for_location,
    remove_file_type_from_location,
)


async def service_add_file_type_to_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
):
    try:
        instance = await add_file_type_to_location(
            db, project_id, location_id, project_file_type_id
        )
        await db.commit()
        return instance
    except Exception as e:
        await db.rollback()
        raise e


async def service_remove_file_type_from_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
):
    try:
        count = await remove_file_type_from_location(
            db, project_id, location_id, project_file_type_id
        )
        await db.commit()
        return count
    except Exception as e:
        await db.rollback()
        raise e


async def service_get_file_types_for_location(
    db: AsyncSession, project_id: int, location_id: int
):
    return await get_file_types_for_location(db, project_id, location_id)
