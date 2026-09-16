"""Recovering a project whose storage went missing, or discarding it.

When a project's folder, .git or elan_files disappears, an administrator either
restores the storage from the recovery backup or deletes the project together
with that backup. Both are only for storage that is actually missing: a backup
can be older than the project, so restoring over intact storage would discard
accepted work, and discarding intact storage would destroy a healthy project.
"""

import shutil
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.project import delete_project_db
from app.model.project import Project
from app.service.git_command_runner import delete_project_folder
from app.service.project_filesystem_sync import ProjectFilesystemSyncService
from app.storage.paths import safe_project_path
from app.utils.project_backup import (
    create_hidden_folder_in_root,
    remove_project_backup,
    restore_project_backup,
)

logger = get_logger()

MISSING_STORAGE_STATES = frozenset(
    {"missing_folder", "missing_git", "missing_elan_files"}
)


class ProjectStorageIntactError(FileExistsError):
    """The project's storage is intact, so it is not a recovery candidate."""


class ProjectRecoveryService:
    """Restore or discard a project whose storage is missing."""

    def __init__(
        self, base_path: Path, filesystem_sync: ProjectFilesystemSyncService
    ) -> None:
        self.base_path = base_path
        self.filesystem_sync = filesystem_sync

    def _require_missing_storage(self, project_name: str) -> None:
        state = self.filesystem_sync.inspect_project(project_name).get("status")
        if state not in MISSING_STORAGE_STATES:
            raise ProjectStorageIntactError(
                "The project storage is intact; recovery is only for missing storage"
            )

    async def restore_from_backup(
        self, db: AsyncSession, project_name: str, user_id: int
    ) -> str:
        """Restore missing storage from the recovery backup, all or nothing.

        Whatever partial storage remains is set aside first. If the restore
        fails, the restored copy is removed and that storage is put back, so the
        project is left exactly as it was and the restore can be retried.
        """
        # Deleted projects are restorable too, so the lookup includes them.
        project = await db.scalar(
            select(Project).where(Project.project_name == project_name).limit(1)
        )
        if project is None:
            raise FileNotFoundError("Project not found")
        self._require_missing_storage(project_name)
        backup = safe_project_path(create_hidden_folder_in_root(), project_name)
        if not (backup / ".git").is_dir():
            raise FileNotFoundError("No recovery backup exists for this project")

        project_path = safe_project_path(self.base_path, project_name)
        set_aside: Path | None = None
        if project_path.exists():
            set_aside = project_path.with_name(
                f".{project_path.name}.pre-restore-{uuid.uuid4().hex}"
            )
            shutil.move(str(project_path), str(set_aside))

        try:
            restore_project_backup(project_name, self.base_path)
            project.deleted_at = None
            await self.filesystem_sync.synchronize(project_name, db, user_id, None)
            await db.commit()
        except Exception as error:
            logger.error(
                "Restoring a project from its backup failed and is being reversed; "
                "error_type=%s",
                safe_exception_type(error),
            )
            await db.rollback()
            delete_project_folder(project_path)
            if set_aside is not None:
                shutil.move(str(set_aside), str(project_path))
            raise

        if set_aside is not None:
            delete_project_folder(set_aside)
        return (
            f"Project '{project_name}' restored from backup and database synchronized."
        )

    async def discard(self, db: AsyncSession, project_name: str) -> None:
        """Delete a project with missing storage, together with its backup.

        The deletion is recorded first. The backup is the last copy of the
        project, so it is removed only once nothing can still fail before the
        project is recorded as deleted.
        """
        if not project_name:
            raise ValueError("Project name is required")
        self._require_missing_storage(project_name)
        try:
            await delete_project_db(db, project_name)
            await db.commit()
        except Exception:
            await db.rollback()
            raise
        delete_project_folder(safe_project_path(self.base_path, project_name))
        remove_project_backup(project_name)
