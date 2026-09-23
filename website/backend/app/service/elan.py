"""Parsing ELAN files and storing their relational projection."""

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.annotation import (
    bulk_create_annotations,
)
from app.crud.annotation_value import bulk_get_or_create_annotation_values
from app.crud.association import (
    get_elan_ids_for_project,
)
from app.crud.eaf_revision import append_eaf_revision
from app.crud.elan_file import (
    delete_elan_file_full,
    get_elan_file_by_filename_and_project,
    store_elan_file_data_in_db,
    sync_elan_file_to_tiers,
)
from app.crud.project import get_project_by_name
from app.crud.tier import (
    create_tier_in_db,
    delete_tiers_for_elan_file,
    get_tier_by_name,
    update_parent_tier,
)
from app.crud.tier_group import delete_tier_groups_for_project_and_elan
from app.elan import PersistedEafFile, document_to_persistence, parse_eaf_path
from app.elan.persistence import PersistedTier
from app.utils.file_processing import ElanFileProcessor

# Get logger for this module
logger = get_logger()


@dataclass(frozen=True, slots=True)
class ElanFileOutcome:
    """What happened to one ELAN file given to the service."""

    status: Literal["processed", "skipped", "updated"]
    filename: str
    elan_id: int


class ElanService:
    """Service for ELAN file operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def parse_elan_file(self, file_path: str) -> PersistedEafFile:
        logger.info("Starting to parse an ELAN file")
        t0 = time.perf_counter()

        file_path_obj = ElanFileProcessor.validate_elan_file(file_path)
        document = parse_eaf_path(file_path_obj)
        file_info = document_to_persistence(document)

        total_time = time.perf_counter() - t0
        logger.info(f"Total parse_elan_file time: {total_time:.3f}s")
        return file_info

    # ==================== STORAGE METHODS ====================

    async def _store_tiers_and_annotations(
        self, tiers_data: list[PersistedTier], elan_id: int
    ) -> None:
        logger.debug(f"Storing {len(tiers_data)} tiers with annotations")
        t0 = time.perf_counter()

        # Bulk get or create all annotation values, get value_map
        t_val_start = time.perf_counter()
        value_map = await bulk_get_or_create_annotation_values(self.db, tiers_data)
        t_val_end = time.perf_counter()
        logger.info(f"AnnotationValue creation took {t_val_end - t_val_start:.3f}s")

        # First pass: create all tiers without parent references
        tier_name_to_id: dict[str, int] = {}
        t_tier_start = time.perf_counter()
        for tier_data in tiers_data:
            tier_obj = await get_tier_by_name(self.db, tier_data["tier_name"], elan_id)
            if not tier_obj:
                tier_obj = await create_tier_in_db(
                    db=self.db,
                    tier_name=tier_data["tier_name"],
                    elan_id=elan_id,
                    linguistic_type_ref=tier_data["linguistic_type_ref"],
                    eaf_attributes=tier_data["eaf_attributes"],
                    parent_tier_id=None,
                )
                logger.debug(
                    f"Created new tier: {tier_data['tier_name']} (ID: {tier_obj.tier_id})"
                )
            else:
                logger.debug(
                    f"Using existing tier: {tier_data['tier_name']} (ID: {tier_obj.tier_id})"
                )
            tier_data["tier_id"] = tier_obj.tier_id
            tier_name_to_id[tier_data["tier_name"]] = tier_obj.tier_id
        t_tier_end = time.perf_counter()
        logger.info(f"Tier creation took {t_tier_end - t_tier_start:.3f}s")

        # Second pass: update parent_tier_id for child tiers using CRUD
        for tier_data in tiers_data:
            parent_name = tier_data.get("parent_tier_name")
            if parent_name:
                parent_id = tier_name_to_id.get(parent_name)
                if parent_id:
                    tier_id = tier_data.get("tier_id")
                    if tier_id:
                        await update_parent_tier(self.db, tier_id, parent_id)

        # Bulk create all annotations for all tiers
        t_ann_start = time.perf_counter()
        await bulk_create_annotations(self.db, tiers_data, elan_id, value_map)
        t_ann_end = time.perf_counter()
        logger.info(
            f"Annotation creation (all tiers) took {t_ann_end - t_ann_start:.3f}s"
        )

        logger.info(
            f"Tier/annotation DB operations took {t_ann_end - t_tier_start:.3f}s"
        )
        total_time = time.perf_counter() - t0
        logger.info(f"Total _store_tiers_and_annotations time: {total_time:.3f}s")

    async def store_elan_file_data(
        self,
        file_info: PersistedEafFile,
        user_id: int,
        project_id: int,
        *,
        commit_changes: bool = True,
        replace_existing_tiers: bool = False,
    ) -> int:
        """Store parsed ELAN file data in the database and sync associations."""
        logger.info("Storing parsed ELAN file data")

        try:
            # Store all ELAN file data and associations using CRUD
            elan_id = await store_elan_file_data_in_db(
                self.db, file_info, user_id, project_id
            )
            await append_eaf_revision(
                self.db,
                elan_id=elan_id,
                sha256=file_info["sha256"],
                raw_xml=file_info["raw_xml"],
                created_by=user_id,
            )
            if replace_existing_tiers:
                await delete_tiers_for_elan_file(self.db, elan_id)

            # Store tiers and annotations (this sets tier["tier_id"])
            await self._store_tiers_and_annotations(file_info["tiers"], elan_id)

            # Now that tiers have IDs, sync associations
            tier_ids = [
                tier_id for tier in file_info["tiers"]
                if (tier_id := tier.get("tier_id")) is not None
            ]
            await sync_elan_file_to_tiers(self.db, elan_id, tier_ids)

            if commit_changes:
                await self.db.commit()
            else:
                await self.db.flush()
            logger.info("Successfully stored parsed ELAN file data")
            return elan_id

        except Exception as e:
            if commit_changes:
                await self.db.rollback()
            logger.error(
                "Failed to store ELAN file data; error_type=%s",
                safe_exception_type(e),
            )
            raise

    async def process_single_file(
        self,
        file_path: str,
        user_id: int,
        project_name: str,
        *,
        commit_changes: bool = True,
    ) -> ElanFileOutcome:
        """Process and store a single ELAN file for the given project."""
        logger.info("Processing one ELAN file")

        # Resolve project name to ID
        project = await get_project_by_name(self.db, project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        # Extract filename for duplicate checking
        filename = Path(file_path).name

        # Check if this file was already processed for this project
        existing_file = await get_elan_file_by_filename_and_project(
            self.db, filename, project.project_id
        )
        if existing_file:
            # Check if it's associated with this project
            project_elan_ids = await get_elan_ids_for_project(
                self.db, project.project_id
            )
            if existing_file.elan_id in project_elan_ids:
                logger.info(
                    "File %s already processed for project %s, skipping",
                    filename,
                    project_name,
                )
                return ElanFileOutcome("skipped", filename, existing_file.elan_id)

        logger.debug("Processing a new ELAN file for a project")
        file_info = self.parse_elan_file(file_path)
        elan_id = await self.store_elan_file_data(
            file_info,
            user_id,
            project.project_id,
            commit_changes=commit_changes,
        )
        logger.info("Successfully processed one ELAN file")
        return ElanFileOutcome("processed", filename, elan_id)

    async def process_single_file_and_update(
        self,
        file_path: str,
        user_id: int,
        project_name: str,
        *,
        commit_changes: bool = True,
    ) -> ElanFileOutcome:
        """Process and update a single ELAN file for the given project."""
        logger.info("Processing one ELAN file update")

        # Resolve project name to ID
        project = await get_project_by_name(self.db, project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        filename = Path(file_path).name
        logger.debug("Updating an ELAN file for a project")

        file_info = self.parse_elan_file(file_path)
        elan_id = await self.store_elan_file_data(
            file_info,
            user_id,
            project.project_id,
            commit_changes=commit_changes,
            replace_existing_tiers=True,
        )
        logger.info("Successfully updated one ELAN file")
        return ElanFileOutcome("updated", filename, elan_id)

    async def delete_elan_files_from_db(
        self, filename: str, project_name: str, *, commit_changes: bool = True
    ) -> bool:
        """Delete all DB data for an ELAN file by filename and project.

        This removes the ELAN file, its tiers, annotations, media links, and cleans up orphans.
        """
        logger.info(
            f"[ELAN-DELETE] Attempting to delete ELAN file '{filename}' from project '{project_name}'."
        )

        # Get the project
        project = await get_project_by_name(self.db, project_name)
        if not project:
            logger.warning(
                f"[ELAN-DELETE] Project '{project_name}' not found for ELAN file deletion."
            )
            return False

        # Get the ELAN file by base filename
        base_filename = Path(filename).name
        elan_file_obj = await get_elan_file_by_filename_and_project(
            self.db, base_filename, project.project_id
        )
        if not elan_file_obj:
            logger.info(
                f"[ELAN-DELETE] ELAN file '{base_filename}' not found in DB for deletion."
            )
            return False

        # Check if the ELAN file is associated with this project
        project_elan_ids = await get_elan_ids_for_project(self.db, project.project_id)
        if elan_file_obj.elan_id not in project_elan_ids:
            logger.warning(
                f"[ELAN-DELETE] ELAN file '{base_filename}' is not associated with project '{project_name}'."
            )
            return False

        try:
            await delete_tier_groups_for_project_and_elan(
                self.db, project.project_id, elan_file_obj.elan_id
            )
            logger.info(
                f"[ELAN-DELETE] Removed associations for ELAN file '{base_filename}' and project '{project_name}'."
            )

            await delete_tiers_for_elan_file(self.db, elan_file_obj.elan_id)
            deleted = await delete_elan_file_full(self.db, elan_file_obj.elan_id)
            if not deleted:
                raise RuntimeError("ELAN file disappeared during deletion")
            if commit_changes:
                await self.db.commit()
            else:
                await self.db.flush()
            return True

        except Exception as e:
            if commit_changes:
                await self.db.rollback()
            logger.error(
                "ELAN file deletion failed; error_type=%s",
                safe_exception_type(e),
            )
            if commit_changes:
                return False
            raise
