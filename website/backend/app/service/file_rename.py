"""Renaming ELAN files across the database, the filesystem and the Git export.

A rename touches three stores that cannot share one transaction. The database
is changed inside a transaction, the filesystem is changed in place, and Git
records the result. Whenever a later step fails, the steps already applied are
reversed so the project never keeps a filename in one store that the others
disagree with.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type, safe_failure_summary
from app.core.exceptions import RenameConflictError
from app.crud.elan_file import (
    get_elan_file_by_filename_and_project,
    get_elan_file_name_by_id,
    update_elan_file_name,
)
from app.crud.project import get_project_id_by_name
from app.schema.responses.git import (
    BulkRenameResponse,
    FileRenameResponse,
    RenameResult,
)
from app.service.git_operations import GitCommandRunner
from app.storage.paths import safe_project_path

logger = get_logger()

ELAN_FILES_DIRECTORY = "elan_files"


@dataclass(frozen=True, slots=True)
class _AppliedRename:
    """A filesystem rename that has already happened and may need reversing."""

    old_path: Path
    new_path: Path


def _revert_filesystem_renames(applied: list[_AppliedRename]) -> None:
    """Undo filesystem renames in reverse order, reporting what could not be."""
    for rename in reversed(applied):
        if not rename.new_path.exists() or rename.old_path.exists():
            continue
        try:
            rename.new_path.rename(rename.old_path)
        except Exception as error:
            logger.warning(
                "Could not roll back an ELAN file rename; error_type=%s",
                safe_exception_type(error),
            )


class FileRenameService:
    """Rename one or many ELAN files inside a single project."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    def _elan_files_directory(self, project_name: str) -> Path:
        project_path = safe_project_path(self.base_path, project_name)
        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")
        # The database records accepted filenames, so the rename must be made
        # on, and committed to, the accepted branch.
        GitCommandRunner(
            project_path, maintain_backup=False
        ).ensure_canonical_checkout()
        return project_path

    async def _conflicting_elan_id(
        self, db: AsyncSession, project_name: str, new_filename: str
    ) -> int | None:
        project_id = await get_project_id_by_name(db, project_name)
        if not project_id:
            return None
        conflicting = await get_elan_file_by_filename_and_project(
            db, new_filename, project_id
        )
        return conflicting.elan_id if conflicting else None

    async def _resolve_paths(
        self, db: AsyncSession, project_path: Path, elan_id: int, new_filename: str
    ) -> tuple[str, Path, Path]:
        """Locate the file being renamed and refuse a name already in use."""
        old_filename = await get_elan_file_name_by_id(db, elan_id)
        if not old_filename:
            raise FileNotFoundError(f"ELAN file with ID {elan_id} not found")

        directory = project_path / ELAN_FILES_DIRECTORY
        old_path = directory / old_filename
        new_path = directory / new_filename

        if not old_path.exists():
            raise FileNotFoundError(
                f"File '{old_filename}' not found in project filesystem"
            )

        if new_path.exists():
            conflict_elan_id = await self._conflicting_elan_id(
                db, project_path.name, new_filename
            )
            raise RenameConflictError(
                f"File '{new_filename}' already exists in project",
                conflict_elan_id=conflict_elan_id,
                message_key="rename_file_conflict",
            )

        return old_filename, old_path, new_path

    async def rename_one(
        self,
        db: AsyncSession,
        project_name: str,
        elan_id: int,
        new_filename: str,
    ) -> FileRenameResponse:
        """Rename a single ELAN file, reversing every step if any step fails."""
        project_path = self._elan_files_directory(project_name)
        old_filename, old_path, new_path = await self._resolve_paths(
            db, project_path, elan_id, new_filename
        )

        applied: list[_AppliedRename] = []
        try:
            await update_elan_file_name(db, elan_id, new_filename)
            old_path.rename(new_path)
            applied.append(_AppliedRename(old_path=old_path, new_path=new_path))

            runner = GitCommandRunner(project_path)
            runner.add_all()
            runner.commit(f"Rename file: {old_filename} -> {new_filename}")
            # `commit` does not return the hash, so read it back from the repo.
            commit_hash = runner.get_commit_hash()
            await db.commit()
        except Exception as error:
            logger.error(
                "ELAN file rename failed; error_type=%s", safe_exception_type(error)
            )
            await db.rollback()
            _revert_filesystem_renames(applied)
            raise RuntimeError("Failed to rename file") from error

        logger.info("Completed an ELAN file rename")
        return FileRenameResponse(
            project_name=project_name,
            old_filename=old_filename,
            new_filename=new_filename,
            success=True,
            committed=True,
            commit_hash=commit_hash,
            renamed_at=datetime.now(UTC).isoformat(),
            message=f"Successfully renamed {old_filename} to {new_filename}",
        )

    async def _apply_one_of_many(
        self,
        db: AsyncSession,
        project_path: Path,
        rename_info: dict[str, Any],
        applied: list[_AppliedRename],
    ) -> RenameResult:
        """Apply one rename of a batch, reporting failure instead of raising."""
        elan_id = rename_info.get("elan_id")
        requested_name = rename_info.get("new_filename")
        requested_name = requested_name if isinstance(requested_name, str) else ""

        try:
            if not isinstance(elan_id, int) or not requested_name:
                raise ValueError("Missing elan_id or new_filename")

            old_filename, old_path, new_path = await self._resolve_paths(
                db, project_path, elan_id, requested_name
            )
            await update_elan_file_name(db, elan_id, requested_name)
            old_path.rename(new_path)
            applied.append(_AppliedRename(old_path=old_path, new_path=new_path))

            return RenameResult(
                old_filename=old_filename,
                new_filename=requested_name,
                success=True,
                error=None,
            )
        except RenameConflictError as error:
            logger.warning(
                "Rename conflict detected; error_type=%s", safe_exception_type(error)
            )
            return RenameResult(
                old_filename=await self._reportable_filename(db, elan_id),
                new_filename=requested_name,
                success=False,
                error="The requested filename conflicts with an existing file",
                conflict_elan_id=error.conflict_elan_id,
                message_key=error.message_key,
            )
        except Exception as error:
            logger.error(
                "File rename failed; error_type=%s", safe_exception_type(error)
            )
            return RenameResult(
                old_filename=await self._reportable_filename(db, elan_id),
                new_filename=requested_name,
                success=False,
                error=safe_failure_summary(error, operation="File rename failed"),
            )

    @staticmethod
    async def _reportable_filename(db: AsyncSession, elan_id: object) -> str:
        """Best-effort current name, used only to describe a failed rename."""
        if not isinstance(elan_id, int):
            return ""
        try:
            return await get_elan_file_name_by_id(db, elan_id) or ""
        except Exception:
            logger.warning("Could not resolve a filename for a failed rename")
            return ""

    @staticmethod
    def _message_key(failed: list[RenameResult], conflicts: int) -> str:
        if conflicts > 0:
            return (
                "bulk_rename_conflicts"
                if conflicts == len(failed)
                else "bulk_rename_mixed_errors"
            )
        return "bulk_rename_errors" if failed else "bulk_rename_success"

    async def rename_many(
        self,
        db: AsyncSession,
        project_name: str,
        renames: list[dict[str, Any]],
    ) -> BulkRenameResponse:
        """Rename several ELAN files, keeping the three stores consistent.

        Individual renames may fail and are reported per file. If committing the
        batch fails, every rename already applied is reversed, so a partially
        written batch is never left behind.
        """
        project_path = self._elan_files_directory(project_name)
        applied: list[_AppliedRename] = []
        succeeded: list[RenameResult] = []
        failed: list[RenameResult] = []

        try:
            for rename_info in renames:
                result = await self._apply_one_of_many(
                    db, project_path, rename_info, applied
                )
                (succeeded if result.success else failed).append(result)

            commit_hash: str | None = None
            if succeeded:
                runner = GitCommandRunner(project_path)
                runner.add_all()
                runner.commit(f"Bulk rename: {len(succeeded)} files")
                commit_hash = runner.get_commit_hash()
                await db.commit()
                logger.info("Completed a bulk ELAN file rename")
            else:
                await db.rollback()
                logger.warning("No files were successfully renamed")
        except Exception as error:
            logger.error(
                "Bulk ELAN file rename failed; error_type=%s",
                safe_exception_type(error),
            )
            await db.rollback()
            _revert_filesystem_renames(applied)
            raise RuntimeError("Bulk rename failed") from error

        conflicts = sum(1 for result in failed if result.conflict_elan_id is not None)
        return BulkRenameResponse(
            project_name=project_name,
            total_files=len(renames),
            successful_renames=len(succeeded),
            failed_renames=len(failed),
            results=succeeded + failed,
            committed=bool(succeeded),
            commit_hash=commit_hash,
            renamed_at=datetime.now(UTC).isoformat(),
            message=(f"Renamed {len(succeeded)}/{len(renames)} files successfully"),
            conflicts_count=conflicts,
            message_key=self._message_key(failed, conflicts),
        )
