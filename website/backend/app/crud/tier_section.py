from sqlalchemy.ext.asyncio import AsyncSession

from app.model.tier_group import TierGroup
from app.model.tier_section import TierSection
from app.utils.database import DatabaseUtils


async def create_tier_section(
    db: AsyncSession, project_id: int, name: str
) -> TierSection:
    section = TierSection(project_id=project_id, section_name=name)
    return await DatabaseUtils.create(db, section)


async def get_tier_sections_by_project(
    db: AsyncSession, project_id: int
) -> list[TierSection]:
    return await DatabaseUtils.get_by_filter(
        db, TierSection, {"project_id": project_id}
    )


async def update_tier_section_name(
    db: AsyncSession, tier_section_id: int, new_name: str
) -> int:
    return await DatabaseUtils.update_by_filter(
        db,
        TierSection,
        {"tier_section_id": tier_section_id},
        {"section_name": new_name},
    )


async def delete_tier_section(db: AsyncSession, tier_section_id: int) -> int:
    # Move all tier groups to unsectioned
    await DatabaseUtils.update_by_filter(
        db, TierGroup, {"section_id": tier_section_id}, {"section_id": None}
    )
    # Now delete the section
    return await DatabaseUtils.delete_by_filter(
        db, TierSection, tier_section_id=tier_section_id, auto_commit=True
    )
