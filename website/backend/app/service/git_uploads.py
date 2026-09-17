"""Writing uploaded files into a project's working tree."""

import subprocess
from collections.abc import Sequence
from pathlib import Path

from fastapi import UploadFile

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type, safe_failure_summary
from app.service import git_backup
from app.service.git_command_runner import GitCommandRunner
from app.service.git_results import FileUploadResult

logger = get_logger()


class FileUploadProcessor:
    """Processes file uploads to Git."""

    def __init__(self, project_path: Path) -> None:
        """Initialize with the project path."""
        self.project_path = project_path

    async def process_files(
        self, files: Sequence[UploadFile], existing_files: list[str]
    ) -> tuple[list[FileUploadResult], list[FileUploadResult]]:
        """Process all uploaded files and return success/failure lists."""
        uploaded_files: list[FileUploadResult] = []
        failed_files: list[FileUploadResult] = []

        for file in files:
            try:
                result = await self._process_single_file(file, existing_files)
                uploaded_files.append(result)
                logger.info("Added an uploaded file to Git")
            except Exception as e:
                filename = file.filename or ""
                failed_result = FileUploadResult(
                    filename=filename,
                    size=file.size or 0,
                    existed=filename in existing_files,
                    success=False,
                    error=safe_failure_summary(e, operation="File processing failed"),
                )
                failed_files.append(failed_result)
                logger.error(
                    "Uploaded file processing failed; error_type=%s",
                    safe_exception_type(e),
                )

        return uploaded_files, failed_files

    async def _process_single_file(
        self, file: UploadFile, existing_files: list[str]
    ) -> FileUploadResult:
        """Process a single file upload."""
        # Ensure elan_files directory exists
        elan_files_dir = self.project_path / "elan_files"
        elan_files_dir.mkdir(exist_ok=True)

        filename = file.filename
        if (
            not filename
            or filename in {".", ".."}
            or "/" in filename
            or "\\" in filename
            or "\x00" in filename
        ):
            raise ValueError("Invalid upload filename")

        dest_path = elan_files_dir / filename
        logger.debug("Processing an uploaded file")

        # Always save the file - let Git determine if it changed
        content = await file.read()
        with open(dest_path, "wb") as buffer:
            buffer.write(content)

        logger.info("Saved an uploaded file; size_bytes=%s", len(content))

        # Add to git - Git will handle change detection
        try:
            runner = GitCommandRunner(self.project_path)
            runner.run(["add", "--", f"elan_files/{filename}"], check=True)
            logger.debug("Staged an uploaded file in Git")

        except subprocess.CalledProcessError as e:
            logger.error(
                "Staging an uploaded file failed; error_type=%s",
                safe_exception_type(e),
            )
            raise RuntimeError("Failed to stage uploaded file") from e

        return FileUploadResult(
            filename=filename,
            size=file.size or 0,
            existed=file.filename in existing_files,
            success=True,
        )

    def commit_files(
        self, uploaded_files: list[FileUploadResult], user_name: str
    ) -> None:
        """Commit all uploaded files with Git's change detection."""
        logger.info(f"Attempting to commit {len(uploaded_files)} files")

        runner = GitCommandRunner(self.project_path)

        # Let Git determine what actually changed
        status_result = runner.run(["status", "--porcelain"])
        staged_files = []

        for line in status_result.stdout.splitlines():
            if line.strip():
                status_code = line[:2]
                filename = line[3:].strip()
                if status_code[0] in ["A", "M", "D"]:  # Staged changes
                    staged_files.append(filename)

        if not staged_files:
            logger.info(
                "No changes detected by Git - all files are identical to existing versions"
            )
            return  # Don't treat this as an error

        logger.info("Git detected %s changed files", len(staged_files))

        # Build commit message based on what Git actually detected
        file_count = len(uploaded_files)
        changed_count = len(staged_files)
        identical_count = file_count - changed_count

        commit_message = f"Batch upload: {file_count} ELAN files"
        if identical_count > 0:
            commit_message += f" ({changed_count} changed, {identical_count} identical)"

        full_message = (
            f"{commit_message}\n\n"
            f"Uploaded by: {user_name}\n"
            f"Files: {', '.join([f.filename for f in uploaded_files])}"
        )

        logger.debug("Prepared an upload commit message")

        try:
            runner.run(["commit", "-m", full_message], check=True)
            git_backup.update_backup(self.project_path.name, self.project_path.parent)
            logger.info(f"Successfully committed {changed_count} changed files")
        except subprocess.CalledProcessError as e:
            if "nothing to commit" in e.stderr:
                logger.info("No changes to commit - all files are identical")
                return  # Success case
            else:
                logger.error(
                    "Committing uploaded files failed; error_type=%s",
                    safe_exception_type(e),
                )
                raise RuntimeError("Failed to commit uploaded files") from e
