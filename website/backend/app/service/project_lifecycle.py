"""Project repository creation and import lifecycle operations."""

import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.crud.project import create_project_db, project_exists_by_name
from app.service.elan import ElanService
from app.service.git_operations import GitCommandRunner, delete_project_folder
from app.service.project_revision import append_project_revision
from app.storage.paths import safe_project_path
from app.utils.project_backup import remove_project_backup, update_backup
from app.utils.project_setup_utils import (
    copy_githooks,
    create_gitignore,
    create_project_structure,
    create_readme,
)

logger = get_logger()


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
                    raise ValueError(f"The imported folder contains duplicate file {filename!r}")
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
                    raise RuntimeError(f"Could not import {elan_file.name}")

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
            except Exception:
                logger.exception("Unable to clean recovery cache for failed import")
            raise

        try:
            update_backup(project_name, self.base_path)
        except Exception:
            logger.exception(
                "Project %r was imported, but its recovery cache could not be updated",
                project_name,
            )
        return {
            "project_name": project_name,
            "path": str(project_path),
            "status": "initialized",
            "git_initialized": True,
            "created_at": datetime.now().isoformat(),
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

        logger.info(f"Checking if project folder exists: {project_path}")
        logger.info(f"Folder exists? {project_path.exists()}")

        if project_path.exists():
            logger.warning(f"Project folder '{project_path}' already exists.")
            raise ValueError(f"Project '{project_name}' already exists")

        exists = await project_exists_by_name(db, project_name)
        logger.info(f"Checking if project exists in DB: {project_name} -> {exists}")
        if exists:
            logger.warning(f"Project '{project_name}' already exists in the database.")
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
            except Exception:
                logger.exception(
                    "Project %r was created, but its recovery cache could not be updated",
                    project_name,
                )

            return {
                "project_name": project_name,
                "path": str(project_path),
                "status": "created",
                "git_initialized": True,
                "created_at": datetime.now().isoformat(),
            }

        except Exception as e:
            await db.rollback()
            logger.exception("Project creation failed for %r", project_name)
            # The path and recovery cache were created by this request. Remove
            # both on failure so filesystem and database state cannot diverge.
            try:
                if published:
                    delete_project_folder(project_path)
                elif staging_path is not None:
                    delete_project_folder(staging_path)
                remove_project_backup(project_name)
            except Exception:
                logger.exception(
                    "Unable to clean up failed project creation for %r", project_name
                )
            raise RuntimeError(f"Project creation failed: {e}") from e
