"""Contribution intake helpers independent from review and publication."""

from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import UploadFile

from app.core.centralized_logging import get_logger
from app.service.git_operations import FileUploadResult, GitCommandRunner

logger = get_logger()


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
        except Exception:
            logger.exception("Unable to clean up failed contribution %s", branch_name)

    @classmethod
    def build_response(
        cls,
        project_name: str,
        uploaded_files: list[FileUploadResult],
        failed_files: list[FileUploadResult],
        existing_files: list[str],
        upload_info: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "project_name": project_name,
            "upload_id": upload_info.get("upload_id"),
            "branch_name": upload_info.get("branch_name"),
            "uploaded_files": [cls._result_dict(item) for item in uploaded_files],
            "failed_files": [cls._result_dict(item) for item in failed_files],
            "total_uploaded": len(uploaded_files),
            "total_failed": len(failed_files),
            "existing_files_updated": len(existing_files),
            "new_files_added": len(uploaded_files) - len(existing_files),
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
