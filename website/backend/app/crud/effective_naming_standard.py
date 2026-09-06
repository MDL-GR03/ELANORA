from sqlalchemy.ext.asyncio import AsyncSession

from app.model.effective_naming_standard import EffectiveNamingStandard
from app.utils.database import DatabaseUtils


async def set_effective_standard(
    db: AsyncSession,
    project_id: int,
    project_file_type_id: int,
    naming_standard_id: int,
    location_id: int,
):
    filters = {
        "project_id": project_id,
        "project_file_type_id": project_file_type_id,
        "location_id": location_id,
    }
    existing = await DatabaseUtils.get_one_by_filter(
        db, EffectiveNamingStandard, filters
    )
    if existing:
        existing.naming_standard_id = naming_standard_id
        await db.flush()
        await db.refresh(existing)
        return existing
    else:
        new_row = EffectiveNamingStandard(
            project_id=project_id,
            project_file_type_id=project_file_type_id,
            naming_standard_id=naming_standard_id,
            location_id=location_id,
        )
        await DatabaseUtils.create(db, new_row)
        await db.flush()
        await db.refresh(new_row)
        return new_row


async def remove_effective_standard(
    db: AsyncSession, project_id: int, project_file_type_id: int, location_id: int
):
    await DatabaseUtils.delete_by_filter(
        db,
        EffectiveNamingStandard,
        project_id=project_id,
        project_file_type_id=project_file_type_id,
        location_id=location_id,
    )
    await db.flush()


async def get_effective_standards_for_project(
    db: AsyncSession, project_id: int, location_id: int
):
    return await DatabaseUtils.get_all_by_filter(
        db,
        EffectiveNamingStandard,
        {"project_id": project_id, "location_id": location_id},
    )
