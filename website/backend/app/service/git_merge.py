"""Merging a reviewed contribution into the accepted project."""

import subprocess
from pathlib import Path
from typing import Any

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.service import git_backup
from app.service.git_command_runner import GitCommandRunner
from app.service.git_results import MergeAnalysis

logger = get_logger()


class GitMerger:
    """Handles Git merge operations."""

    def __init__(self, project_path: Path):
        """Initialize with the project path."""
        self.project_path = project_path

    def selective_merge_with_conflict_isolation(
        self, branch_name: str, analysis: MergeAnalysis
    ) -> dict[str, Any]:
        """Perform selective merge: auto-merge safe files, isolate conflicts."""
        logger.info("Starting selective Git merge")
        logger.info(
            f"Analysis summary - New files: {len(analysis.new_files)}, Modified: {len(analysis.modified_files)}, Deleted: {len(analysis.deleted_files)}"
        )

        if not analysis.has_conflicts:
            logger.info("No conflicts detected, performing auto-merge")
            return self._perform_auto_merge(branch_name, analysis.new_files)

        logger.info("Conflicts detected, proceeding with selective merge strategy")
        # If we have conflicts, perform selective merge
        return self._perform_selective_merge(branch_name, analysis)

    def _perform_selective_merge(
        self, branch_name: str, analysis: MergeAnalysis
    ) -> dict[str, Any]:
        """Merge only non-conflicting files, isolate problematic ones."""
        logger.info("Performing selective Git merge")
        runner = GitCommandRunner(self.project_path)

        conflict_branch_name = f"{branch_name}_conflicts"

        try:
            # Start from master and create conflict branch
            runner.checkout("master")
            runner.run(["checkout", "-b", conflict_branch_name], check=True)
            logger.info("Created an isolated conflict branch")

            # Cherry-pick ONLY modified files to conflict branch
            if analysis.modified_files:
                logger.info(
                    f"Adding {len(analysis.modified_files)} modified files to conflict branch"
                )
                for modified_file in analysis.modified_files:
                    try:
                        # Get the modified version from upload branch
                        runner.run(
                            ["checkout", branch_name, "--", modified_file], check=True
                        )
                        logger.debug("Added a modified file to the conflict branch")
                    except subprocess.CalledProcessError as e:
                        logger.warning(
                            "Could not add a modified file; error_type=%s",
                            safe_exception_type(e),
                        )

                # Commit only the modified files
                runner.add_all()
                runner.commit(f"Modified files from {branch_name} for review")
                logger.info("Successfully created conflict branch with modified files")

            # Switch to upload branch and remove ALL conflicting content
            runner.checkout(branch_name)

            # Remove modified files (reset to master version = remove changes)
            if analysis.modified_files:
                logger.info(
                    f"Resetting {len(analysis.modified_files)} modified files to master version"
                )
                for modified_file in analysis.modified_files:
                    try:
                        runner.run(
                            ["checkout", "master", "--", modified_file], check=True
                        )
                        logger.debug("Reset a modified file to the canonical version")
                    except subprocess.CalledProcessError as e:
                        logger.warning(
                            "Could not reset a modified file; error_type=%s",
                            safe_exception_type(e),
                        )

            # Handle deleted files (restore them from master)
            if analysis.deleted_files:
                logger.info(
                    f"Restoring {len(analysis.deleted_files)} deleted files from master"
                )
                for deleted_file in analysis.deleted_files:
                    try:
                        runner.run(
                            ["checkout", "master", "--", deleted_file], check=True
                        )
                        logger.debug(
                            "Restored a deleted file from the canonical branch"
                        )
                    except subprocess.CalledProcessError as e:
                        logger.debug(
                            "Could not restore a deleted file; error_type=%s",
                            safe_exception_type(e),
                        )

            # Commit the cleanup (this makes upload branch have only new files)
            if analysis.modified_files or analysis.deleted_files:
                runner.add_all()
                runner.commit("Remove conflicting changes - keep only new files")
                logger.info("Cleaned upload branch to contain only new files")

            # Merge clean upload branch to master
            runner.checkout("master")

            # Check what's actually different (should be only new files now)
            files_to_merge = analysis.new_files.copy()

            if files_to_merge:
                merge_message = (
                    f"Add {len(files_to_merge)} new files from {branch_name}"
                )
                runner.merge(branch_name, merge_message, no_ff=True)
                logger.info(f"Successfully merged {len(files_to_merge)} new files")
            else:
                logger.info("No new files to merge")

            # Clean up upload branch
            runner.delete_branch(branch_name)

            return {
                "status": "selective_merge_completed",
                "has_conflicts": True,
                "has_differences": True,
                "merged_files": files_to_merge,
                "conflict_files": analysis.modified_files,
                "conflict_branch": conflict_branch_name,
                "deleted_files": analysis.deleted_files,
                "message": f"Merged {len(files_to_merge)} new files. {len(analysis.modified_files)} modified files isolated for review in '{conflict_branch_name}'",
                "analysis": analysis,
            }

        except Exception as e:
            # Cleanup on error
            try:
                runner.checkout("master")
                runner.run(["branch", "-D", conflict_branch_name], check=False)
                runner.run(["branch", "-D", branch_name], check=False)
            except Exception as cleanup_error:
                logger.error(
                    "Failed to clean up branches after selective merge; error_type=%s",
                    safe_exception_type(cleanup_error),
                )
            raise RuntimeError("Selective merge failed") from e

    def auto_merge_if_safe(
        self, branch_name: str, analysis: MergeAnalysis
    ) -> dict[str, Any]:
        """Automatically merge if only new files, otherwise return conflict info."""
        logger.info("Checking whether a contribution can be merged automatically")

        if not analysis.has_conflicts:
            logger.info("No conflicts detected, proceeding with auto-merge")
            return self._perform_auto_merge(branch_name, analysis.new_files)
        else:
            logger.warning(
                f"Conflicts detected in branch '{branch_name}', returning conflict response"
            )
            return self._create_conflict_response(branch_name, analysis)

    def _perform_auto_merge(
        self, branch_name: str, new_files: list[str]
    ) -> dict[str, Any]:
        """Perform automatic merge for new files only."""
        logger.info(
            f"Performing auto-merge for branch '{branch_name}' with {len(new_files)} new files"
        )

        merge_message = f"Merge batch upload branch '{branch_name}' into master - {len(new_files)} new files added"
        logger.debug("Prepared an automatic merge commit message")

        try:
            subprocess.run(
                [
                    "git",
                    "merge",
                    branch_name,
                    "--no-ff",
                    "-m",
                    merge_message,
                ],
                cwd=self.project_path,
                check=True,
            )
            git_backup.update_backup(self.project_path.name, self.project_path.parent)
            logger.info(
                f"Successfully auto-merged {len(new_files)} new files from branch '{branch_name}'"
            )

            return {
                "status": "merged_successfully",
                "has_conflicts": False,
                "has_differences": True,
                "new_files": new_files,
                "modified_files": [],
                "deleted_files": [],
                "message": f"Successfully merged {len(new_files)} new files",
            }
        except subprocess.CalledProcessError as e:
            logger.error(
                "Automatic merge failed; error_type=%s", safe_exception_type(e)
            )
            raise RuntimeError("Automatic merge failed") from e

    def _create_conflict_response(
        self, branch_name: str, analysis: MergeAnalysis
    ) -> dict[str, Any]:
        """Create response for conflicts that need review."""
        logger.info("Creating a contribution conflict response")
        logger.info(
            f"Conflict summary - Modified: {analysis.modified_files}, Deleted: {analysis.deleted_files}"
        )

        # Get summary stats
        try:
            detailed_diff = subprocess.run(
                ["git", "diff", f"master...{branch_name}", "--stat"],
                cwd=self.project_path,
                capture_output=True,
                text=True,
                check=False,
            )
            logger.debug("Generated contribution diff statistics")
        except Exception as e:
            logger.error(
                "Generating diff statistics failed; error_type=%s",
                safe_exception_type(e),
            )
            detailed_diff = subprocess.CompletedProcess([], 0, "", "")

        logger.warning(
            f"Conflicts detected in branch '{branch_name}' - modified files: {analysis.modified_files}"
        )

        return {
            "status": "changes_detected",
            "has_conflicts": True,
            "has_differences": True,
            "new_files": analysis.new_files,
            "modified_files": analysis.modified_files,
            "deleted_files": analysis.deleted_files,
            "diff_summary": detailed_diff.stdout,
            "file_changes": analysis.file_changes,
            "branch_name": branch_name,
            "message": f"Conflicts detected - {len(analysis.modified_files)} modified files require review",
        }
