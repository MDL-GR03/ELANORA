"""Project repository creation, import, rename and deletion lifecycle."""

import shutil
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.project import (
    create_project_db,
    delete_project_db,
    get_project_by_name,
    project_exists_by_name,
)
from app.model.project import Project
from app.service.elan import ElanService
from app.service.git_operations import GitCommandRunner, delete_project_folder
from app.service.project_revision import append_project_revision
from app.storage.paths import safe_project_path
from app.utils.project_backup import (
    create_hidden_folder_in_root,
    remove_project_backup,
    update_backup,
)
from app.utils.project_setup_utils import (
    copy_githooks,
    create_gitignore,
    create_project_structure,
    create_readme,
    update_project_githooks,
)

logger = get_logger()


class ProjectNameUnavailableError(FileExistsError):
    """The name belongs to another project, including a retained deleted one.

    A deleted project keeps its record and recovery cache so it can be restored
    by name, and restoring it writes to the folder of that name.
    """


class ProjectLifecycleService:
    """Create and import project repositories while preserving atomicity."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    async def import_project(
        self,
        project_name: str,
        description: str,
        files: list[UploadFile],
        db: AsyncSession,
        user_id: int,
        instance_id: int,
    ) -> dict[str, Any]:
        """Atomically import EAF files as a new project and initial revision."""
        project_path = safe_project_path(self.base_path, project_name)
        if project_path.exists() or await project_exists_by_name(db, project_name):
            raise ValueError(f"Project '{project_name}' already exists")

        staging_path: Path | None = None
        published = False
        try:
            staging_path = Path(
                tempfile.mkdtemp(prefix=f".{project_name}.staging-", dir=self.base_path)
            )
            elan_files_dir = staging_path / "elan_files"
            elan_files_dir.mkdir(parents=True)
            create_gitignore(staging_path)
            create_readme(staging_path, project_name)

            saved_files: list[Path] = []
            saved_names: set[str] = set()
            for upload in files:
                if not upload.filename or not upload.filename.lower().endswith(".eaf"):
                    continue
                filename = Path(upload.filename).name
                if filename in saved_names:
                    raise ValueError(
                        f"The imported folder contains duplicate file {filename!r}"
                    )
                saved_names.add(filename)
                destination = elan_files_dir / filename
                with destination.open("wb") as output:
                    while chunk := await upload.read(1024 * 1024):
                        output.write(chunk)
                saved_files.append(destination)
            if not saved_files:
                raise ValueError("The imported folder does not contain any EAF files")

            runner = GitCommandRunner(staging_path, maintain_backup=False)
            runner.init_repo()
            runner.add_all()
            runner.commit("Initial commit from uploaded folder")
            initial_commit = runner.get_commit_hash()

            project = await create_project_db(
                db=db,
                project_name=project_name,
                description=description or "",
                project_path=str(project_path),
                instance_id=instance_id,
                creator_user_id=user_id,
            )
            # Process from the canonical location so persisted file paths never
            # retain the temporary staging directory name. The DB transaction
            # remains uncommitted, and failures remove this directory again.
            staging_path.rename(project_path)
            published = True
            elan_service = ElanService(db)
            processed_files: list[str] = []
            skipped_files: list[str] = []
            for staged_file in sorted(saved_files):
                elan_file = project_path / "elan_files" / staged_file.name
                result = await elan_service.process_single_file(
                    str(elan_file), user_id, project_name, commit_changes=False
                )
                status = result.get("status")
                if status == "processed":
                    processed_files.append(str(result["filename"]))
                elif status == "skipped":
                    skipped_files.append(str(result["filename"]))
                else:
                    raise RuntimeError("Could not import an ELAN file")

            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=initial_commit,
                parent_git_commit=None,
                source_type="migration",
                actor_user_id=user_id,
                details={"message": "Initial imported project revision"},
            )
            await db.commit()
        except Exception:
            await db.rollback()
            cleanup_path = project_path if published else staging_path
            if cleanup_path is not None and cleanup_path.exists():
                delete_project_folder(cleanup_path)
            try:
                remove_project_backup(project_name)
            except Exception as cleanup_error:
                logger.error(
                    "Unable to clean recovery cache for failed import; error_type=%s",
                    safe_exception_type(cleanup_error),
                )
            raise

        try:
            update_backup(project_name, self.base_path)
        except Exception as backup_error:
            logger.error(
                "An imported project's recovery cache could not be updated; "
                "error_type=%s",
                safe_exception_type(backup_error),
            )
        return {
            "project_name": project_name,
            "path": str(project_path),
            "status": "initialized",
            "git_initialized": True,
            "created_at": datetime.now(UTC).isoformat(),
            "processed_files": processed_files,
            "skipped_files": skipped_files,
        }

    async def create_project(
        self,
        project_name: str,
        description: str | None,
        db: AsyncSession,
        user_id: int,
        instance_id: int,
    ) -> dict[str, Any]:
        """Create a new project with Git repository and description."""
        project_path = safe_project_path(self.base_path, project_name)
        staging_path: Path | None = None
        published = False

        logger.info("Checking whether the project directory exists")

        if project_path.exists():
            logger.warning("The project directory already exists")
            raise ValueError(f"Project '{project_name}' already exists")

        exists = await project_exists_by_name(db, project_name)
        logger.info("Checked whether the project exists in the database")
        if exists:
            logger.warning("The project already exists in the database")
            raise ValueError(f"Project '{project_name}' already exists")

        try:
            # Assemble the complete repository out of sight, on the same
            # filesystem as its final location so publication is atomic.
            staging_path = Path(
                tempfile.mkdtemp(prefix=f".{project_name}.staging-", dir=self.base_path)
            )
            create_project_structure(staging_path)
            runner = GitCommandRunner(staging_path, maintain_backup=False)
            runner.init_repo()

            # Create .gitignore and README
            create_gitignore(staging_path)
            create_readme(staging_path, project_name)

            # Copy githooks
            copy_githooks(staging_path, project_name)

            # Initial commit
            runner.add_all()
            runner.commit("Initial project setup")

            # Paths
            hooks_dir = staging_path / ".git" / "hooks"
            hooks_dir.mkdir(parents=True, exist_ok=True)

            # Save to database
            project = await create_project_db(
                db=db,
                project_name=project_name,
                description=description or "",
                project_path=str(project_path),
                instance_id=instance_id,
                creator_user_id=user_id,
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=runner.get_commit_hash(),
                parent_git_commit=None,
                source_type="migration",
                actor_user_id=user_id,
                details={"message": "Initial project setup"},
            )
            # Flush has succeeded in create_project_db, but PostgreSQL remains
            # uncommitted while the ready repository is atomically published.
            staging_path.rename(project_path)
            published = True
            await db.commit()

            # The recovery cache is derived state. Build it only after both
            # authoritative stores have accepted the project.
            try:
                update_backup(project_name, self.base_path)
            except Exception as backup_error:
                logger.error(
                    "A new project's recovery cache could not be updated; error_type=%s",
                    safe_exception_type(backup_error),
                )

            return {
                "project_name": project_name,
                "path": str(project_path),
                "status": "created",
                "git_initialized": True,
                "created_at": datetime.now(UTC).isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.error(
                "Project creation failed; error_type=%s", safe_exception_type(e)
            )
            # The path and recovery cache were created by this request. Remove
            # both on failure so filesystem and database state cannot diverge.
            try:
                if published:
                    delete_project_folder(project_path)
                elif staging_path is not None:
                    delete_project_folder(staging_path)
                remove_project_backup(project_name)
            except Exception:
                logger.error("Unable to clean up failed project creation")
            raise RuntimeError("Project creation failed") from e

    async def _name_is_held_by_another_project(
        self, db: AsyncSession, project: Project, name: str, path: Path
    ) -> bool:
        holder = await db.scalar(
            select(Project.project_id)
            .where(
                Project.project_id != project.project_id,
                or_(Project.project_name == name, Project.project_path == str(path)),
            )
            .limit(1)
        )
        return holder is not None

    @staticmethod
    def _restore_moves(moved: list[tuple[Path, Path]]) -> None:
        """Put moved folders back, newest first, reporting any that cannot be."""
        for current, original in reversed(moved):
            try:
                shutil.move(str(current), str(original))
            except Exception as error:
                logger.error(
                    "Could not restore a folder moved by a failed project rename; "
                    "error_type=%s",
                    safe_exception_type(error),
                )

    async def rename_project(
        self,
        db: AsyncSession,
        old_project_name: str,
        new_project_name: str,
        new_project_description: str | None,
    ) -> dict[str, str | None]:
        """Rename a project's folder, recovery backup and record as one change.

        Every precondition is checked, and the record is flushed, before anything
        on disk moves. If a later step fails, the database is rolled back and each
        moved folder is put back, so no store is left under a different name.
        """
        project = await get_project_by_name(db, old_project_name)
        if not project:
            raise ValueError("Project not found in database")

        if new_project_name == old_project_name:
            project.description = new_project_description
            await db.commit()
            return {
                "new_project_name": new_project_name,
                "new_project_description": new_project_description,
            }

        old_path = safe_project_path(self.base_path, old_project_name)
        new_path = safe_project_path(self.base_path, new_project_name)
        if not old_path.exists():
            raise FileNotFoundError("Project directory not found")
        if new_path.exists():
            raise FileExistsError("Target project directory already exists")
        if await self._name_is_held_by_another_project(
            db, project, new_project_name, new_path
        ):
            raise ProjectNameUnavailableError(
                "The requested name belongs to another project"
            )

        backup_root = create_hidden_folder_in_root()
        old_backup = safe_project_path(backup_root, old_project_name)
        new_backup = safe_project_path(backup_root, new_project_name)
        if new_backup.exists():
            raise ProjectNameUnavailableError(
                "A recovery backup already exists under the requested name"
            )

        project.project_name = new_project_name
        project.project_path = str(new_path)
        project.description = new_project_description
        # Surface constraint violations while nothing on disk has changed.
        try:
            await db.flush()
        except Exception:
            await db.rollback()
            raise

        moved: list[tuple[Path, Path]] = []
        try:
            shutil.move(str(old_path), str(new_path))
            moved.append((new_path, old_path))
            # A project that has no recovery cache yet has nothing to move.
            if old_backup.exists():
                shutil.move(str(old_backup), str(new_backup))
                moved.append((new_backup, old_backup))
            update_project_githooks(new_path, new_project_name)
            await db.commit()
        except Exception as error:
            logger.error(
                "Project rename failed and is being reversed; error_type=%s",
                safe_exception_type(error),
            )
            await db.rollback()
            self._restore_moves(moved)
            if moved:
                try:
                    update_project_githooks(old_path, old_project_name)
                except Exception as hook_error:
                    logger.warning(
                        "Could not restore project Git hooks after a failed rename; "
                        "error_type=%s",
                        safe_exception_type(hook_error),
                    )
            raise

        logger.info("Renamed a project folder, backup and record together")
        return {
            "new_project_name": new_project_name,
            "new_project_description": new_project_description,
        }

    async def delete_project(self, db: AsyncSession, project_name: str) -> None:
        """Retain the project record as deleted, then remove its working folder."""
        if not project_name:
            raise ValueError("Project name is required")
        try:
            await delete_project_db(db, project_name)
            await db.commit()
        except Exception as error:
            await db.rollback()
            logger.error(
                "Failed to delete project database records; error_type=%s",
                safe_exception_type(error),
            )
            raise
        delete_project_folder(safe_project_path(self.base_path, project_name))
