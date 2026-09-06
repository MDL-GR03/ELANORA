from sqlalchemy.ext.asyncio import AsyncSession

from app.model.project_location_file_type import ProjectLocationFileType
from app.utils.database import DatabaseUtils


async def add_file_type_to_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
):
    instance = ProjectLocationFileType(
        project_id=project_id,
        location_id=location_id,
        project_file_type_id=project_file_type_id,
    )
    await DatabaseUtils.create(db, instance)
    await db.flush()
    return instance


async def remove_file_type_from_location(
    db: AsyncSession, project_id: int, location_id: int, project_file_type_id: int
):
    count = await DatabaseUtils.delete_by_filter(
        db,
        ProjectLocationFileType,
        project_id=project_id,
        location_id=location_id,
        project_file_type_id=project_file_type_id,
    )
    await db.flush()
    return count


async def get_file_types_for_location(
    db: AsyncSession, project_id: int, location_id: int
):
    return await DatabaseUtils.get_by_filter(
        db,
        ProjectLocationFileType,
        {"project_id": project_id, "location_id": location_id},
    )
