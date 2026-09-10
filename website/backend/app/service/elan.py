"""ELAN Service - Simplified using utilities."""

import time
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.annotation import (
    bulk_create_annotations,
    delete_annotations_by_tier,
    get_annotations_by_tier,
    get_annotations_by_time_range,
)
from app.crud.annotation_value import bulk_get_or_create_annotation_values
from app.crud.association import (
    get_elan_ids_for_project,
)
from app.crud.eaf_revision import append_eaf_revision
from app.crud.elan_file import (
    delete_elan_file_full,
    get_all_elan_files,
    get_elan_file_by_filename_and_project,
    get_elan_files_by_user,
    store_elan_file_data_in_db,
    sync_elan_file_to_tiers,
)
from app.crud.project import get_project_by_name
from app.crud.tier import (
    create_tier_in_db,
    delete_tiers_for_elan_file,
    get_all_tier_names_with_annotations,
    get_tier_by_name,
    get_tier_statistics,
    get_tiers_with_annotations,
    update_parent_tier,
)
from app.crud.tier_group import delete_tier_groups_for_project_and_elan
from app.elan import PersistedEafFile, document_to_persistence, parse_eaf_path
from app.model.tier import Tier
from app.utils.file_processing import ElanFileProcessor

# Get logger for this module
logger = get_logger()


class ElanService:
    """Service for ELAN file operations."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.file_processor = ElanFileProcessor()

    def parse_elan_file(self, file_path: str) -> PersistedEafFile:
        logger.info(f"Starting to parse ELAN file: {file_path}")
        t0 = time.perf_counter()

        file_path_obj = ElanFileProcessor.validate_elan_file(file_path)
        document = parse_eaf_path(file_path_obj)
        file_info = document_to_persistence(document)

        total_time = time.perf_counter() - t0
        logger.info(f"Total parse_elan_file time: {total_time:.3f}s")
        return file_info

    def get_files_in_directory(self, directory_path: str) -> list[Path]:
        """Get all ELAN files in a flat directory using utility."""
        logger.info(f"Scanning directory for ELAN files: {directory_path}")
        files = ElanFileProcessor.find_files_in_directory(directory_path, "*.eaf")
        logger.info(f"Found {len(files)} ELAN files in directory")
        return files

    # ==================== STORAGE METHODS ====================

    async def _store_tiers_and_annotations(
        self, tiers_data: list[dict], elan_id: int
    ) -> None:
        logger.debug(f"Storing {len(tiers_data)} tiers with annotations")
        t0 = time.perf_counter()

        # Bulk get or create all annotation values, get value_map
        t_val_start = time.perf_counter()
        value_map = await bulk_get_or_create_annotation_values(self.db, tiers_data)
        t_val_end = time.perf_counter()
        logger.info(f"AnnotationValue creation took {t_val_end - t_val_start:.3f}s")

        # First pass: create all tiers without parent references
        tier_name_to_id = {}
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
                if parent_id and tier_data.get("parent_tier_id") != parent_id:
                    await update_parent_tier(self.db, tier_data["tier_id"], parent_id)

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
        self, file_info: dict, user_id: int, project_id: int
    ) -> int:
        """Store parsed ELAN file data in the database and sync associations."""
        logger.info(f"Storing ELAN file data: {file_info['filename']}")

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

            # Store tiers and annotations (this sets tier["tier_id"])
            await self._store_tiers_and_annotations(file_info["tiers"], elan_id)

            # Now that tiers have IDs, sync associations
            tier_ids = [tier["tier_id"] for tier in file_info["tiers"]]
            await sync_elan_file_to_tiers(self.db, elan_id, tier_ids)

            await self.db.commit()
            logger.info(f"Successfully stored: {file_info['filename']} (ID: {elan_id})")
            return elan_id

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to store ELAN file data for {file_info['filename']}: {e}"
            )
            raise

    async def update_elan_file_data(
        self, file_info: dict, user_id: int, project_id: int
    ) -> int:
        """Store parsed ELAN file data in the database and sync associations."""
        logger.info(f"Storing ELAN file data: {file_info['filename']}")
        try:
            existing_file = await get_elan_file_by_filename_and_project(
                self.db, file_info["filename"], project_id
            )
            if existing_file:
                logger.info(f"Updating existing ELAN file: {existing_file.elan_id}")
            else:
                logger.info(f"No existing ELAN file found for {file_info['filename']}")
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
            await delete_tiers_for_elan_file(self.db, elan_id)

            # Store tiers and annotations (this sets tier["tier_id"])
            await self._store_tiers_and_annotations(file_info["tiers"], elan_id)

            # Now that tiers have IDs, sync associations
            tier_ids = [tier["tier_id"] for tier in file_info["tiers"]]
            await sync_elan_file_to_tiers(self.db, elan_id, tier_ids)

            await self.db.commit()
            logger.info(f"Successfully stored: {file_info['filename']} (ID: {elan_id})")
            return elan_id

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Failed to store ELAN file data for {file_info['filename']}: {e}"
            )
            raise

    async def process_single_file(
        self, file_path: str, user_id: int, project_name: str
    ) -> dict:
        """Process and store a single ELAN file for the given project."""
        logger.info("Processing single ELAN file: %s", file_path)

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
                return {
                    "status": "skipped",
                    "reason": "already_processed",
                    "filename": filename,
                    "elan_id": existing_file.elan_id,
                }

        logger.debug("Processing new file: %s for project: %s", filename, project_name)
        file_info = self.parse_elan_file(file_path)
        elan_id = await self.store_elan_file_data(
            file_info, user_id, project.project_id
        )
        logger.info("Successfully processed file: %s with ID: %d", filename, elan_id)
        return {"status": "processed", "filename": filename, "elan_id": elan_id}

    async def process_single_file_and_update(
        self, file_path: str, user_id: int, project_name: str
    ) -> dict:
        """Process and update a single ELAN file for the given project."""
        logger.info("Processing single ELAN file for update: %s", file_path)

        # Resolve project name to ID
        project = await get_project_by_name(self.db, project_name)
        if not project:
            raise ValueError(f"Project '{project_name}' not found")

        filename = Path(file_path).name
        logger.debug("Updating file: %s for project: %s", filename, project_name)

        file_info = self.parse_elan_file(file_path)
        elan_id = await self.update_elan_file_data(
            file_info, user_id, project.project_id
        )
        logger.info("Successfully updated file: %s with ID: %d", filename, elan_id)
        return {"status": "updated", "filename": filename, "elan_id": elan_id}

    async def process_directory(
        self, directory_path: str, user_id: int, project_name: str
    ) -> dict[str, dict]:
        """Process all ELAN files in a flat directory for the given project."""
        logger.info("Starting directory processing: %s", directory_path)
        eaf_files = self.get_files_in_directory(directory_path)

        logger.info("Found %d ELAN files in %s", len(eaf_files), directory_path)

        results = {}
        processed_count = 0
        skipped_count = 0
        failed_count = 0

        for eaf_file in eaf_files:
            try:
                logger.debug("Processing: %s", eaf_file.name)
                result = await self.process_single_file(
                    str(eaf_file), user_id, project_name
                )
                results[eaf_file.name] = result

                if result["status"] == "processed":
                    processed_count += 1
                    logger.debug("Successfully processed: %s", result["filename"])
                elif result["status"] == "skipped":
                    skipped_count += 1
                    logger.debug("Skipped existing file: %s", result["filename"])

            except Exception as e:
                logger.error("Failed to process %s: %s", eaf_file.name, e)
                results[eaf_file.name] = {
                    "status": "failed",
                    "filename": eaf_file.name,
                    "error": str(e),
                }
                failed_count += 1

        logger.info(
            "Directory processing completed. Processed: %d, Skipped: %d, Failed: %d",
            processed_count,
            skipped_count,
            failed_count,
        )

        if skipped_count > 0:
            skipped_files = [
                result["filename"]
                for result in results.values()
                if result["status"] == "skipped"
            ]
            logger.info("Skipped files (already in database): %s", skipped_files)

        return results

    # ==================== QUERY METHODS ====================

    async def get_all_files_with_tiers(self) -> dict[str, list[str]]:
        """Get all files with their associated tier names."""
        logger.debug("Retrieving all files with their tier names")

        tier_names = await get_all_tier_names_with_annotations(self.db)
        files = await get_all_elan_files(self.db)

        logger.debug(
            f"Found {len(files)} files with {len(tier_names)} unique tier types"
        )

        return {f.filename: tier_names for f in files}

    async def get_file_structure(self, filename: str, project_id: int) -> dict | None:
        """Get complete structure for a specific file."""
        logger.debug(f"Retrieving file structure for: {filename}")

        # Get file using CRUD
        elan_file_obj = await get_elan_file_by_filename_and_project(
            self.db, filename, project_id
        )

        if not elan_file_obj:
            logger.warning(f"File not found in database: {filename}")
            return None

        # Get all tiers with annotations
        tiers_with_annotations = await self._get_tiers_with_annotations()

        file_structure = {
            "elan_id": elan_file_obj.elan_id,
            "filename": elan_file_obj.filename,
            "file_path": elan_file_obj.file_path,
            "file_size": elan_file_obj.file_size,
            "tiers": [],
        }

        total_annotations = 0
        for tier_obj in tiers_with_annotations:
            # Get annotations using CRUD
            annotations_list = await get_annotations_by_tier(self.db, tier_obj.tier_id)
            tier_data = {
                "tier_id": tier_obj.tier_id,
                "tier_name": tier_obj.tier_name,
                "parent_tier_id": tier_obj.parent_tier_id,
                "annotation_count": len(annotations_list),
                "annotations": [
                    {
                        "annotation_id": ann.annotation_id,
                        "annotation_value": ann.annotation_value,
                        "start_time": float(ann.start_time),
                        "end_time": float(ann.end_time),
                    }
                    for ann in annotations_list
                ],
            }
            file_structure["tiers"].append(tier_data)
            total_annotations += len(annotations_list)

        logger.debug(
            f"Retrieved structure for {filename}: {len(file_structure['tiers'])} tiers, {total_annotations} annotations"
        )
        return file_structure

    async def _get_tiers_with_annotations(self) -> list[Tier]:
        """Get all tiers that have at least one annotation."""
        tiers = await get_tiers_with_annotations(self.db)
        logger.debug(f"Found {len(tiers)} tiers with annotations")
        return tiers

    async def get_tier_statistics(self) -> dict:
        """Get statistics about tiers across all files."""
        logger.debug("Generating tier statistics")

        stats_list = await get_tier_statistics(self.db)
        stats = {
            "tier_statistics": [
                {"tier_name": tier_name, "annotation_count": ann_count}
                for tier_name, ann_count in stats_list
            ]
        }

        logger.debug(
            f"Generated statistics for {len(stats['tier_statistics'])} tier types"
        )
        return stats

    async def get_user_files(self, user_id: int) -> list[dict]:
        """Get all ELAN files for a specific user."""
        logger.debug(f"Retrieving files for user ID: {user_id}")

        # Use CRUD function
        files = await get_elan_files_by_user(self.db, user_id)

        logger.debug(f"Found {len(files)} files for user {user_id}")

        return [
            {
                "elan_id": f.elan_id,
                "filename": f.filename,
                "file_path": f.file_path,
                "file_size": f.file_size,
            }
            for f in files
        ]

    async def get_annotations_in_time_range(
        self, tier_id: int, start_time: Decimal, end_time: Decimal
    ) -> list[dict]:
        """Get annotations within a specific time range for a tier."""
        logger.debug(
            f"Retrieving annotations for tier {tier_id} in time range: {start_time}-{end_time}"
        )

        # Use CRUD function
        annotations_list = await get_annotations_by_time_range(
            self.db, tier_id, start_time, end_time
        )

        logger.debug(f"Found {len(annotations_list)} annotations in time range")

        return [
            {
                "annotation_id": ann.annotation_id,
                "annotation_value": ann.annotation_value,
                "start_time": float(ann.start_time),
                "end_time": float(ann.end_time),
            }
            for ann in annotations_list
        ]

    async def delete_tier_annotations(self, tier_id: int) -> int:
        """Delete all annotations for a specific tier."""
        logger.info(f"Deleting all annotations for tier ID: {tier_id}")

        # Use CRUD function
        deleted_count = await delete_annotations_by_tier(self.db, tier_id)

        logger.info(f"Deleted {deleted_count} annotations for tier {tier_id}")
        return deleted_count

    async def delete_elan_files_from_db(self, filename: str, project_name: str) -> bool:
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
            await delete_elan_file_full(self.db, elan_file_obj.elan_id)
            await self.db.commit()
            return True

        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"[ELAN-DELETE] Error during deletion of ELAN file '{base_filename}': {e}"
            )
            return False
