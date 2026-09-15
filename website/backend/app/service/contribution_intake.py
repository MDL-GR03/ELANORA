"""Contribution intake helpers independent from review and publication."""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.pending_upload import get_pending_uploads, save_pending_upload
from app.crud.project import get_project_by_name
from app.service.git_operations import (
    FileUploadResult,
    GitBranchManager,
    GitCommandRunner,
    GitDiffAnalyzer,
)

logger = get_logger()


@dataclass(frozen=True, slots=True)
class SubmissionContext:
    """Authenticated provenance and validation evidence for one upload batch."""

    username: str
    user_id: int
    base_commit: str
    protocol_validation: dict[str, str | None]
    research_context: dict[str, Any]


class DuplicatePendingContributionError(ValueError):
    """Raised when an identical project snapshot is already awaiting review."""

    def __init__(self, upload_id: int) -> None:
        self.upload_id = upload_id
        super().__init__(
            f"This exact contribution is already awaiting review as contribution #{upload_id}."
        )


class ContributionAlreadyCurrentError(ValueError):
    """Raised when submitted files do not change the accepted project state."""


class ContributionIntakeService:
    """Validate, prepare, and describe researcher contribution intake."""

    @staticmethod
    def validate_request(project_path: Path, files: list[UploadFile]) -> None:
        if not project_path.exists():
            raise FileNotFoundError(
                f"Project not found at the specified path: {project_path}"
            )
        if not files:
            raise ValueError("No files provided")
        if any(not upload.filename for upload in files):
            raise ValueError("All files must have filenames")

    @staticmethod
    def existing_files(project_path: Path, files: list[UploadFile]) -> list[str]:
        return [
            filename
            for upload in files
            if (filename := upload.filename)
            and (project_path / "elan_files" / filename).exists()
        ]

    @staticmethod
    def configure_git_user(project_path: Path, instance_name: str) -> None:
        GitCommandRunner(project_path).configure_user(instance_name)

    @staticmethod
    def discard_failed_submission(project_path: Path, branch_name: str) -> None:
        """Return to accepted work and remove branches from a failed submission."""
        runner = GitCommandRunner(project_path, maintain_backup=False)
        try:
            runner.checkout(runner.canonical_branch())
            runner.delete_branch_localy(branch_name)
            runner.delete_branch_localy(f"{branch_name}_pending_approval")
        except Exception as error:
            logger.error(
                "Unable to clean up a failed contribution; error_type=%s",
                safe_exception_type(error),
            )

    async def record_pending_submission(
        self,
        branch_manager: GitBranchManager,
        diff_analyzer: GitDiffAnalyzer,
        branch_name: str,
        db: AsyncSession,
        context: SubmissionContext,
        project_path: Path,
        *,
        allow_current_tree: bool = False,
    ) -> dict[str, Any]:
        """Deduplicate, analyze, and durably record a submitted Git tree."""
        project = await get_project_by_name(db, project_path.name)
        if project is None:
            raise FileNotFoundError("Project disappeared while recording contribution")

        runner = GitCommandRunner(project_path)
        submitted_tree = runner.get_tree_hash(branch_name)
        if not allow_current_tree and submitted_tree == runner.get_tree_hash(
            runner.canonical_branch()
        ):
            raise ContributionAlreadyCurrentError(
                "These files are already the current accepted version; no contribution was created."
            )
        await self._reject_duplicate_tree(
            db, project.project_id, runner, submitted_tree
        )

        branch_manager.switch_to_master()
        analysis = diff_analyzer.analyze_merge_differences(branch_name)
        approval_branch = f"{branch_name}_pending_approval"
        try:
            runner.run(["branch", "-m", branch_name, approval_branch], check=True)
            now = datetime.now().isoformat()
            upload_info: dict[str, Any] = {
                "status": "pending_admin_approval",
                "has_conflicts": False,
                "has_differences": bool(
                    analysis.modified_files or analysis.deleted_files
                ),
                "requires_approval": True,
                "branch_name": approval_branch,
                "original_branch": branch_name,
                "new_files": analysis.new_files,
                "modified_files": analysis.modified_files,
                "deleted_files": analysis.deleted_files,
                "analysis": analysis,
                "message": (
                    "Upload saved for admin approval. "
                    f"{len(analysis.new_files)} new files, "
                    f"{len(analysis.modified_files)} modified files."
                ),
                "pending_approval_since": now,
                "uploaded_by": context.username,
                "base_commit": context.base_commit,
                "protocol_validation": context.protocol_validation,
                "research_context": context.research_context,
            }
            await self._save_pending_upload(
                upload_info, project.project_id, db, context
            )
            return upload_info
        except Exception as exc:
            runner.run(["branch", "-D", approval_branch], check=False)
            raise RuntimeError("Failed to save upload for approval") from exc

    @staticmethod
    async def _reject_duplicate_tree(
        db: AsyncSession,
        project_id: int,
        runner: GitCommandRunner,
        submitted_tree: str,
    ) -> None:
        for pending in await get_pending_uploads(db, project_id):
            if not pending.branch_name:
                continue
            try:
                if runner.get_tree_hash(pending.branch_name) == submitted_tree:
                    raise DuplicatePendingContributionError(pending.upload_id)
            except DuplicatePendingContributionError:
                raise
            except Exception:
                logger.warning(
                    "Could not inspect pending contribution branch %s",
                    pending.branch_name,
                )

    @staticmethod
    async def _save_pending_upload(
        upload_info: dict[str, Any],
        project_id: int,
        db: AsyncSession,
        context: SubmissionContext,
    ) -> None:
        upload_record = {
            "type": "PENDING_UPLOAD",
            "status": "PENDING_ADMIN_APPROVAL",
            "upload_data": {
                "branch_name": upload_info["branch_name"],
                "original_branch": upload_info["original_branch"],
                "uploaded_by": context.username,
                "new_files_count": len(upload_info["new_files"]),
                "modified_files_count": len(upload_info["modified_files"]),
                "deleted_files_count": len(upload_info["deleted_files"]),
                "new_files": upload_info["new_files"],
                "modified_files": upload_info["modified_files"],
                "deleted_files": upload_info["deleted_files"],
                "pending_since": upload_info["pending_approval_since"],
                "has_differences": upload_info["has_differences"],
                "has_conflicts": upload_info["has_conflicts"],
                "protocol_validation": upload_info["protocol_validation"],
                "research_context": upload_info["research_context"],
            },
            "resolution_info": {
                "can_auto_resolve": False,
                "requires_admin_approval": True,
                "suggested_action": "admin_test_merge",
                "available_strategies": ["test_merge"],
            },
            "detected_at": upload_info["pending_approval_since"],
        }
        pending = await save_pending_upload(
            db,
            project_id,
            upload_info["branch_name"],
            upload_record,
            submitted_by=context.user_id,
            base_commit=context.base_commit,
        )
        upload_info["upload_id"] = pending.upload_id

    @classmethod
    def build_response(
        cls,
        project_name: str,
        uploaded_files: list[FileUploadResult],
        failed_files: list[FileUploadResult],
        upload_info: dict[str, Any],
    ) -> dict[str, Any]:
        # Counted from what was actually written, so a requested file that failed
        # is neither an update nor an addition.
        updated = sum(1 for item in uploaded_files if item.existed)
        return {
            "project_name": project_name,
            "upload_id": upload_info.get("upload_id"),
            "branch_name": upload_info.get("branch_name"),
            "uploaded_files": [cls._result_dict(item) for item in uploaded_files],
            "failed_files": [cls._result_dict(item) for item in failed_files],
            "total_uploaded": len(uploaded_files),
            "total_failed": len(failed_files),
            "existing_files_updated": updated,
            "new_files_added": len(uploaded_files) - updated,
            "status": upload_info["status"],
            "requires_approval": upload_info.get("requires_approval", True),
            "has_differences": upload_info.get("has_differences", False),
            "auto_accepted": upload_info.get("auto_accepted", False),
            "upload_summary": {
                "new_files": upload_info.get("new_files", []),
                "modified_files": upload_info.get("modified_files", []),
                "deleted_files": upload_info.get("deleted_files", []),
            },
            "admin_info": {
                "pending_approval_since": upload_info.get("pending_approval_since"),
                "approval_branch": upload_info.get("branch_name"),
                "original_branch": upload_info.get("original_branch"),
                "next_steps": "Upload saved for admin approval. Admin needs to test merge and resolve any conflicts.",
            },
            "uploaded_at": datetime.now().isoformat(),
            "message": upload_info.get(
                "message", "Upload completed and saved for admin approval"
            ),
        }

    @staticmethod
    def _result_dict(result: FileUploadResult) -> dict[str, Any]:
        return {
            "filename": result.filename,
            "size": result.size,
            "existed": result.existed,
        }
