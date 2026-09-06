"""Database operations for handling Git-detected renames."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.elan_file import (
    get_elan_file_by_filename_and_project,
    update_elan_file_name,
)
from app.crud.project import get_project_by_name

logger = get_logger()


class DatabaseRenameHandler:
    """Handles database updates for Git-detected file renames."""

    def __init__(self, db: AsyncSession):
        """Initialize with database session."""
        self.db = db

    async def process_rename(
        self, old_filename: str, new_filename: str, project_name: str
    ) -> bool:
        """Process a rename by updating the database filename.

        Args:
            old_filename: The original filename
            new_filename: The new filename
            project_name: The project name

        Returns:
            bool: True if successful, False otherwise

        """
        try:
            logger.info(f"Processing rename in DB: {old_filename} -> {new_filename}")

            # Get the project
            project = await get_project_by_name(self.db, project_name)
            if not project:
                logger.warning(f"Could not find project {project_name}")
                return False

            # Get the elan_file for the old filename
            elan_file = await get_elan_file_by_filename_and_project(
                self.db, old_filename, project.project_id
            )
            if not elan_file:
                logger.warning(
                    f"Could not find elan_file for {old_filename} in project {project_name}"
                )
                return False

            # Update the filename in database
            await update_elan_file_name(self.db, elan_file.elan_id, new_filename)
            logger.info(
                f"Successfully renamed file in DB: {old_filename} -> {new_filename} (elan_id: {elan_file.elan_id})"
            )

            return True

        except Exception as e:
            logger.error(
                f"Failed to process rename {old_filename} -> {new_filename}: {e}"
            )
            return False
