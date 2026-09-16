"""Reconciling a project's ELAN files on disk with the database and Git.

Administrators may edit a project folder directly. Synchronization reads what
Git reports about that folder, refuses the whole batch if any changed EAF would
not survive ingestion, and only then stages and records the result. Inspection
uses the same reading but must never stage or alter anything.
"""

from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_MAX_FILE_SIZE_MB
from app.core.error_diagnostics import safe_exception_type
from app.elan.validation import validate_eaf
from app.schema.responses.git import FileStatus, ProjectSyncCheckResponse
from app.service.database_rename_handler import DatabaseRenameHandler
from app.service.elan import ElanService
from app.service.git_command_runner import GitCommandRunner
from app.service.git_status_parser import GitFileStatusAnalyzer, GitStatusParser
from app.storage.paths import safe_project_path

logger = get_logger()


class ProjectFilesystemSyncService:
    """Reconcile a project folder with its database projection."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    @staticmethod
    def _analyze_changes(
        runner: GitCommandRunner, elan_files_dir: Path
    ) -> tuple[list[FileStatus], list[Any]]:
        """Read Git's view of the folder. Shared so preview and apply agree."""
        status_output = runner.get_status()
        analyzer = GitFileStatusAnalyzer(GitStatusParser())
        tracked = set(runner.run(["ls-files"], check=True).stdout.strip().splitlines())
        logger.info("Found %s tracked project files", len(tracked))
        return analyzer.analyze_project_files(status_output, tracked, elan_files_dir)

    async def synchronize(
        self,
        project_name: str,
        db: AsyncSession,
        user_id: int,
        operation_id: str | None = None,
    ) -> dict[str, Any]:
        """Idempotently synchronize the project's elan_files with the database."""
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)

        logger.info("Starting project synchronization")

        # Server edits are committed to the checked-out branch, which must be the
        # accepted one. Edits on a stray branch are refused, not committed there.
        runner.ensure_canonical_checkout()

        # Inspect first. Nothing is staged until every changed EAF passes preflight.
        elan_files_dir = project_path / "elan_files"
        files_status, processed_files = self._analyze_changes(runner, elan_files_dir)
        logger.info(
            "Analyzed project files; processed=%s changed=%s",
            len(processed_files),
            len(files_status),
        )

        elan_service = ElanService(db)
        updated_files = []
        deleted_files = []

        logger.info(f"Processing {len(files_status)} file status changes")

        self._validate_sync_candidates(project_path, files_status)

        # Establish the Git snapshot only after the complete batch passes validation.
        runner.add_all()

        for file_status in files_status:
            filename = file_status.filename
            status = file_status.status
            file_path = project_path / filename

            logger.info("Processing a project file with status=%s", status)

            try:
                if status in {"added", "untracked"}:
                    if file_path.exists():
                        logger.info("Adding a new ELAN file to the database")
                        await elan_service.process_single_file(
                            str(file_path), user_id, project_name
                        )
                        updated_files.append(file_path)
                        logger.info("Added a new ELAN file to the database")
                    else:
                        logger.warning(
                            f"File marked as {status} but doesn't exist: {file_path}"
                        )
                elif status == "modified":
                    if file_path.exists():
                        logger.info("Updating a modified ELAN file in the database")
                        await elan_service.process_single_file_and_update(
                            str(file_path), user_id, project_name
                        )
                        updated_files.append(file_path)
                        logger.info("Updated a modified ELAN file in the database")
                    else:
                        logger.warning(
                            f"File marked as modified but doesn't exist: {file_path}"
                        )
                elif status == "deleted":
                    logger.info("Removing a deleted project file from the database")
                    await elan_service.delete_elan_files_from_db(filename, project_name)
                    deleted_files.append(filename)
                    logger.info("Deleted a project file from the database")
                elif status == "renamed":
                    # Handle Git-detected renames by updating database filename
                    old_filename = file_status.old_filename
                    new_filename = file_status.new_filename

                    logger.info("Processing a project file rename")

                    if old_filename and new_filename:
                        # Extract just the filename from the full path for database lookup
                        old_filename_only = Path(old_filename).name
                        new_filename_only = Path(new_filename).name

                        logger.info(
                            f"Database rename: {old_filename_only} -> {new_filename_only}"
                        )
                        rename_handler = DatabaseRenameHandler(db)
                        success = await rename_handler.process_rename(
                            old_filename_only, new_filename_only, project_name
                        )
                        if success:
                            updated_files.append(project_path / new_filename)
                        else:
                            logger.warning(
                                f"Failed to process rename: {old_filename_only} -> {new_filename_only}"
                            )
                    else:
                        logger.warning(
                            f"Rename detected but missing old/new filename info: {file_status}"
                        )
                else:
                    logger.warning("Unknown project file status=%s", status)
            except Exception as e:
                logger.error(
                    "Failed to synchronize a project file; status=%s error_type=%s",
                    status,
                    safe_exception_type(e),
                )
                await db.rollback()
                raise RuntimeError("Failed to synchronize a project file") from e

        # Commit database changes if any were made
        await db.commit()
        logger.info("Database changes committed")

        # Commit changes if any
        status_output = runner.get_status()
        if status_output.strip():
            message = f"Synchronized project '{project_name}' with ELAN files"
            if operation_id:
                message += f"\n\nELANORA-Sync-Operation: {operation_id}"
            runner.commit(message)

        logger.info("Project synchronization completed")

        # Return a status/check response
        return ProjectSyncCheckResponse(
            project_name=project_name,
            in_sync=True,
            files_status=[
                FileStatus(
                    filename=str(f), status="updated", description="File updated"
                )
                for f in updated_files
            ]
            + [
                FileStatus(filename=f, status="deleted", description="File deleted")
                for f in deleted_files
            ],
        ).model_dump()

    def validate_changes(
        self, project_name: str, changes: list[dict[str, object]]
    ) -> None:
        """Apply the canonical EAF preflight to a serialized preview."""
        project_path = safe_project_path(self.base_path, project_name)
        self._validate_sync_candidates(
            project_path, [FileStatus.model_validate(change) for change in changes]
        )

    @staticmethod
    def _validate_sync_candidates(
        project_path: Path, files_status: list[FileStatus]
    ) -> None:
        """Reject a recovery batch before staging if any changed EAF is unsafe."""
        for file_status in files_status:
            if file_status.status == "deleted":
                continue
            candidate = project_path / file_status.filename
            if not candidate.exists() and file_status.new_filename:
                candidate = project_path / file_status.new_filename
            if not candidate.is_file():
                raise ValueError(
                    f"Changed ELAN file is missing: {file_status.filename}"
                )
            if candidate.stat().st_size > ELAN_MAX_FILE_SIZE_MB * 1024 * 1024:
                raise ValueError(
                    f"Changed ELAN file exceeds {ELAN_MAX_FILE_SIZE_MB}MB: {candidate.name}"
                )
            validate_eaf(candidate.read_bytes())

    def inspect_project(self, project_name: str) -> dict[str, Any]:
        """Check for changes in a Git-managed project and analyze file status.

        Analyzes the Git status to detect file changes in the elan_files directory
        and compares against tracked files to determine sync status.

        Args:
            project_name: Name of the project to check for changes

        Returns:
            Dictionary containing project sync status and file change information

        """
        project_path = safe_project_path(self.base_path, project_name)
        elan_files_dir = project_path / "elan_files"
        git_dir = project_path / ".git"

        logger.info("Checking project synchronization state")

        if not project_path.exists():
            return {
                "project_name": project_name,
                "status": "missing_folder",
                "in_sync": False,
                "files_status": [],
            }
        if not git_dir.exists():
            return {
                "project_name": project_name,
                "status": "missing_git",
                "in_sync": False,
                "files_status": [],
            }
        if not elan_files_dir.exists():
            return {
                "project_name": project_name,
                "status": "missing_elan_files",
                "in_sync": False,
                "files_status": [],
            }

        # Preview must not stage or otherwise alter administrator edits.
        runner = GitCommandRunner(project_path)
        files_status, processed_files = self._analyze_changes(runner, elan_files_dir)

        logger.info(
            "Analyzed project synchronization state; processed=%s changed=%s",
            len(processed_files),
            len(files_status),
        )

        in_sync = not bool(files_status)

        return ProjectSyncCheckResponse(
            project_name=project_name, in_sync=in_sync, files_status=files_status
        ).model_dump()

    def discard_local_changes(self, project_name: str) -> str:
        """Discard server edits and leave the accepted repository version checked out.

        Uncommitted work is dropped where it is, then the tree returns to the
        accepted branch. Only that branch is ever reset, so no other branch, such
        as one left by an interrupted upload, is rewritten.
        """
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        runner.reset_hard()
        runner.clean(force=True, directories=True)
        runner.ensure_canonical_checkout()
        if "origin" in runner.run(["remote", "-v"]).stdout.strip():
            logger.info("Found a configured project Git remote")
            runner.run(["fetch", "origin"], check=True)
            runner.reset_hard(f"origin/{runner.canonical_branch()}")
            runner.clean(force=True, directories=True)
        else:
            logger.warning("No project Git remote is configured")
        return "Local changes discarded and folder reset to match the latest remote master."
