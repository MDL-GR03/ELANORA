"""Contribution branches and the differences between them."""

import re
import secrets
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from app.core.centralized_logging import get_logger
from app.service.git_command_runner import GitCommandRunner
from app.service.git_diff_parser import GitDiffParser
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

    def __init__(self, project_path: Path):
        """Initialize with the project path."""
        self.project_path = project_path

    def analyze_merge_differences(self, branch_name: str) -> MergeAnalysis:
        """Analyze differences and return structured data with parsed diffs."""
        logger.info(
            f"Analyzing merge differences for branch '{branch_name}' using Git diff"
        )
        diff_parser = GitDiffParser()

        canonical = GitCommandRunner(
            self.project_path, maintain_backup=False
        ).canonical_branch()
        diff_name_status_result = subprocess.run(
            ["git", "diff", f"{canonical}...{branch_name}", "--name-status"],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            check=False,
        )

        logger.debug("Generated a Git name-status diff")

        new_files, modified_files, deleted_files = diff_parser.parse_name_status_output(
            diff_name_status_result.stdout
        )

        has_conflicts = len(modified_files) > 0 or len(deleted_files) > 0

        logger.info(
            f"Git diff analysis - New: {len(new_files)}, Modified: {len(modified_files)}, Deleted: {len(deleted_files)}"
        )

        file_diffs = {}

        # For each modified file, parse the diff ONCE
        for filename in modified_files:
            file_diff_result = subprocess.run(
                ["git", "diff", f"{canonical}...{branch_name}", "--", filename],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )

            if file_diff_result.stdout:
                parsed_diff = diff_parser.parse_single_file_diff(
                    file_diff_result.stdout
                )
                file_diffs[filename] = parsed_diff  # STORE PARSED DATA

        return MergeAnalysis(
            new_files=new_files,
            modified_files=modified_files,
            deleted_files=deleted_files,
            has_conflicts=has_conflicts,
            file_diffs=file_diffs,
        )
