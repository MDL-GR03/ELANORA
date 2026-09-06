from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.effective_naming_standard import (
    get_effective_standards_for_project,
    remove_effective_standard,
    set_effective_standard,
)


async def assign_effective_standard(
    db: AsyncSession,
    project_id: int,
    project_file_type_id: int,
    naming_standard_id: int,
    location_id: int,
):
    try:
        result = await set_effective_standard(
            db, project_id, project_file_type_id, naming_standard_id, location_id
        )
        await db.commit()
        return result
    except Exception as e:
        await db.rollback()
        raise e


async def unassign_effective_standard(
    db: AsyncSession, project_id: int, project_file_type_id: int, location_id: int
):
    try:
        await remove_effective_standard(
            db, project_id, project_file_type_id, location_id
        )
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise e


async def fetch_effective_standards(
    db: AsyncSession, project_id: int, location_id: int
):
    return await get_effective_standards_for_project(db, project_id, location_id)
