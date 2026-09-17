"""Contribution branches and the differences between them."""

import re
import secrets
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.core.centralized_logging import get_logger
from app.service.git_command_runner import GitCommandRunner
from app.service.git_diff_parser import parse_name_status
from app.service.git_results import MergeAnalysis

logger = get_logger()


class GitBranchManager:
    """Handles Git branch operations."""

    def __init__(self, project_path: Path):
        """Initialize with the project path."""
        self.project_path = project_path
        self.commandRunner = GitCommandRunner(project_path)

    def create_upload_branch(self, user_name: str, file_count: int) -> str:
        """Create a unique branch for file uploads.

        A timestamp alone repeats when one person uploads twice within a second,
        so a random token keeps names distinct. The user name arrives from a
        form field and is reduced to characters that are always valid in a ref.
        """
        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        safe_user = re.sub(r"[^A-Za-z0-9_-]+", "-", user_name).strip("-")[:40]
        branch_name = (
            f"upload_batch_{safe_user or 'contributor'}_{timestamp}_"
            f"{secrets.token_hex(4)}_{file_count}_files"
        )

        subprocess.run(
            ["git", "checkout", "-b", branch_name],
            cwd=self.project_path,
            check=True,
        )
        logger.info("Created and switched to a contribution branch")
        return branch_name

    def switch_to_master(self) -> None:
        """Switch to the repository's canonical branch."""
        branch = self.commandRunner.canonical_branch()
        self.commandRunner.checkout(branch)
        logger.info("Switched to the canonical branch")

    def delete_branch(self, branch_name: str) -> None:
        """Delete a branch."""
        self.commandRunner.delete_branch(branch_name)
        logger.info("Deleted a contribution branch")


class GitDiffAnalyzer:
    """Analyzes Git differences between branches."""

    def __init__(self, project_path: Path) -> None:
        self.project_path = project_path

    def analyze_merge_differences(self, branch_name: str) -> MergeAnalysis:
        """Which files a branch adds, modifies and deletes from the accepted line."""
        canonical = GitCommandRunner(
            self.project_path, maintain_backup=False
        ).canonical_branch()
        result = subprocess.run(
            ["git", "diff", f"{canonical}...{branch_name}", "--name-status"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            check=False,
        )
        changes = parse_name_status(result.stdout)
        logger.info(
            "Git diff analysis - new: %s, modified: %s, deleted: %s",
            len(changes.new_files),
            len(changes.modified_files),
            len(changes.deleted_files),
        )
        return MergeAnalysis(
            new_files=changes.new_files,
            modified_files=changes.modified_files,
            deleted_files=changes.deleted_files,
            has_conflicts=bool(changes.modified_files or changes.deleted_files),
        )
