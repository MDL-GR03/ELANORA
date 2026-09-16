from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.association import get_elan_ids_for_project
from app.crud.elan_file import get_elan_file_by_id
from app.crud.project import get_project_by_id, get_project_id_by_name
from app.crud.tier import get_tiers_by_elan_id
from app.crud.tier_group import (
    get_tier_groups_by_project,
    update_tier_group_section,
)
from app.crud.tier_section import (
    create_tier_section,
    delete_tier_section,
    get_tier_sections_by_project,
    update_tier_section_name,
)
from app.model.tier import Tier
from app.model.tier_section import TierSection
from app.schema.responses.tier import (
    SectionInfo,
    SectionsAndGroupsResponse,
    TierGroupInfo,
    TierNode,
)

logger = get_logger()


class TierService:
    """Service class for handling tier-related operations."""

    @staticmethod
    def build_tier_tree(tiers: list[Tier]) -> list[TierNode]:
        tier_map = {tier.tier_id: tier for tier in tiers}
        children_map: dict[int, list[Tier]] = {tier.tier_id: [] for tier in tiers}
        for tier in tiers:
            if tier.parent_tier_id and tier.parent_tier_id in tier_map:
                children_map[tier.parent_tier_id].append(tier)

        roots = [
            tier
            for tier in tiers
            if not tier.parent_tier_id or tier.parent_tier_id not in tier_map
        ]

        def serialize(tier: Tier) -> TierNode:
            return TierNode(
                tier_id=tier.tier_id,
                tier_name=tier.tier_name,
                parent_tier_id=tier.parent_tier_id,
                children=[serialize(child) for child in children_map[tier.tier_id]],
            )

        return [serialize(root) for root in roots]

    @staticmethod
    async def get_project_tiers_grouped_by_file(
        db: AsyncSession, project_name: str
    ) -> dict[str, dict[str, list[TierNode]]]:
        project_id = await get_project_id_by_name(db, project_name)
        if not project_id:
            logger.error(f"Project not found: {project_name}")
            return {}

        elan_ids = await get_elan_ids_for_project(db, project_id)
        if not elan_ids:
            return {}

        result: dict[str, list[TierNode]] = {}
        for elan_id in elan_ids:
            elan_file = await get_elan_file_by_id(db, elan_id)
            if not elan_file:
                continue
            tiers = await get_tiers_by_elan_id(db, elan_id)
            if not tiers:
                result[elan_file.filename] = []
                continue
            result[elan_file.filename] = TierService.build_tier_tree(tiers)

        return {"tiers": result}


class TierSectionService:
    @staticmethod
    async def create_section(
        db: AsyncSession, project_id: int, name: str
    ) -> TierSection:
        try:
            section = await create_tier_section(db, project_id, name)
            await db.commit()
            return section
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def rename_section(
        db: AsyncSession, tier_section_id: int, new_name: str
    ) -> int:
        try:
            section = await update_tier_section_name(db, tier_section_id, new_name)
            await db.commit()
            return section
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_section(db: AsyncSession, tier_section_id: int) -> int:
        try:
            result = await delete_tier_section(db, tier_section_id)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def get_sections_and_groups(
        db: AsyncSession, project_id: int
    ) -> SectionsAndGroupsResponse:
        sections = await get_tier_sections_by_project(db, project_id)
        tier_groups = await get_tier_groups_by_project(db, project_id)

        project = await get_project_by_id(db, project_id)
        if not project:
            return SectionsAndGroupsResponse(sections=[], tier_groups=[])
        tiers_by_file = await TierService.get_project_tiers_grouped_by_file(
            db, project.project_name
        )
        tiers_dict = tiers_by_file.get("tiers", {})

        return SectionsAndGroupsResponse(
            sections=[
                SectionInfo(section_id=s.tier_section_id, name=s.section_name)
                for s in sections
            ],
            tier_groups=[
                TierGroupInfo(
                    tier_group_id=g.tier_group_id,
                    elan_file_name=g.elan_file_name,
                    section_id=g.section_id,
                    tiers=tiers_dict.get(g.elan_file_name, []),
                )
                for g in tier_groups
            ],
        )


class TierGroupService:
    @staticmethod
    async def assign_group_to_section(
        db: AsyncSession, tier_group_id: int, section_id: int | None
    ) -> int:
        try:
            result = await update_tier_group_section(db, tier_group_id, section_id)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            raise
