import os
import re
import secrets
import shutil
import stat
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type, safe_failure_summary
from app.service.git_diff_parser import GitDiffParser
from app.utils.project_backup import update_backup

logger = get_logger()


@dataclass
class FileUploadResult:
    """Result of uploading a single file."""

    filename: str
    size: int
    existed: bool
    success: bool
    error: str | None = None


@dataclass
class MergeAnalysis:
    """Analysis of merge differences."""

    new_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    has_conflicts: bool
    file_diffs: dict[str, dict] | None = None


@dataclass(frozen=True, slots=True)
class MergeReadiness:
    """A non-mutating merge-tree result for a submitted branch."""

    status: str
    conflicted_files: list[str]

    @property
    def can_merge(self) -> bool:
        return self.status == "ready_to_merge"


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
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
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
            update_backup(self.project_path.name, self.project_path.parent)
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


class FileUploadProcessor:
    """Processes file uploads to Git."""

    def __init__(self, project_path: Path):
        """Initialize with the project path."""
        self.project_path = project_path

    async def process_files(
        self, files, existing_files: list[str]
    ) -> tuple[list[FileUploadResult], list[FileUploadResult]]:
        """Process all uploaded files and return success/failure lists."""
        uploaded_files = []
        failed_files = []

        for file in files:
            try:
                result = await self._process_single_file(file, existing_files)
                uploaded_files.append(result)
                logger.info("Added an uploaded file to Git")
            except Exception as e:
                failed_result = FileUploadResult(
                    filename=file.filename,
                    size=file.size or 0,
                    existed=file.filename in existing_files,
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
        self, file, existing_files: list[str]
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
            update_backup(self.project_path.name, self.project_path.parent)
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


class WorkingTreeOffAcceptedBranchError(RuntimeError):
    """The canonical working tree is off its accepted branch with local changes."""


class GitCommandRunner:
    """Runs generic git commands and returns results."""

    def __init__(self, project_path: Path, *, maintain_backup: bool = True) -> None:
        self.project_path = project_path
        self.maintain_backup = maintain_backup

    def _update_backup(self) -> None:
        if self.maintain_backup:
            update_backup(self.project_path.name, self.project_path.parent)

    def run(
        self, args: list[str], check: bool = False
    ) -> subprocess.CompletedProcess[str]:
        # Project repositories commonly live on bind mounts whose host UID does not
        # match the container user. Trust only this already-resolved repository for
        # this command instead of mutating Git's process-global safe.directory list.
        safe_directory = self.project_path.resolve()
        return subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={safe_directory}",
                "-c",
                "core.quotepath=false",
                *args,
            ],
            cwd=self.project_path,
            capture_output=True,
            text=True,
            check=check,
        )

    def run_bytes(
        self, args: list[str], check: bool = False
    ) -> subprocess.CompletedProcess[bytes]:
        """Run Git without decoding output, for byte-exact repository blobs."""
        safe_directory = self.project_path.resolve()
        return subprocess.run(
            [
                "git",
                "-c",
                f"safe.directory={safe_directory}",
                "-c",
                "core.quotepath=false",
                *args,
            ],
            cwd=self.project_path,
            capture_output=True,
            check=check,
        )

    def get_status(self) -> str:
        return self.run(["status", "--porcelain"], check=True).stdout

    def canonical_branch(self) -> str:
        """Support modern `main` projects and retained legacy `master` projects."""
        for branch in ("main", "master"):
            result = self.run(
                ["show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
                check=False,
            )
            if result.returncode == 0:
                return branch
        raise RuntimeError("Project has no main or master branch")

    def preview_merge(self, branch_name: str) -> MergeReadiness:
        """Inspect a three-way merge without touching HEAD, index, or worktree."""
        result = self.run(
            [
                "merge-tree",
                "--write-tree",
                "--name-only",
                self.canonical_branch(),
                branch_name,
            ],
            check=False,
        )
        if result.returncode == 0:
            return MergeReadiness("ready_to_merge", [])

        lines = result.stdout.splitlines()
        conflicted_files: list[str] = []
        # With --name-only, merge-tree prints the tree id followed by the
        # unmerged paths, then a blank line and human-readable messages.
        for line in lines[1:]:
            candidate = line.strip()
            if not candidate:
                break
            conflicted_files.append(candidate)
        if not conflicted_files:
            raise RuntimeError("Git could not inspect the contribution")
        return MergeReadiness("needs_resolution", conflicted_files)

    def stage_all_changes(self) -> None:
        """Stage all changes to enable rename detection."""
        self.run(["add", "-A"], check=True)

    def get_status_with_renames(self) -> str:
        """Get status after staging changes to detect renames."""
        self.stage_all_changes()
        return self.get_status()

    def get_log(self, count: int = 5) -> str:
        return self.run(
            ["log", f"-{count}", "--pretty=format:%h|%an|%ad|%s", "--date=iso"]
        ).stdout

    def get_conflicted_files(self) -> list[str]:
        result = self.run(["diff", "--name-only", "--diff-filter=U"])
        return [
            line.strip() for line in result.stdout.strip().split("\n") if line.strip()
        ]

    def get_conflict_details(self, filename: str) -> dict[str, Any]:
        file_path = self.project_path / filename
        if file_path.exists():
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                content = f.read()
            conflict_markers = content.count("<<<<<<< HEAD")
            return {
                "conflict_markers_count": conflict_markers,
                "file_size": len(content),
                "has_binary_conflict": "<<<<<<< HEAD" not in content,
            }
        return {"error": "File not found"}

    def configure_user(self, instance_name: str):
        """Configure Git user using the instance name."""
        # Clean the instance name for use in email (lowercase, no spaces)
        safe_name = instance_name.lower().replace(" ", "_")
        email = f"{safe_name}@elanora.local"
        self.run(["config", "user.name", instance_name], check=True)
        self.run(["config", "user.email", email], check=True)
        logger.info("Configured the project Git publication identity")
        self._update_backup()

    def get_branches(self) -> list[str]:
        result = self.run(["branch", "-a"], check=True)
        return result.stdout.strip().split("\n")

    def reset_hard(self, ref: str = "HEAD"):
        self.run(["reset", "--hard", ref], check=True)

    def clean(self, force: bool = True, directories: bool = True):
        args = ["clean"]
        if force:
            args.append("-f")
        if directories:
            args.append("-d")
        self.run(args, check=True)

    def checkout(self, branch: str):
        self.run(["checkout", branch], check=True)

    def canonical_head(self) -> str:
        """Return the accepted branch's commit, whatever is checked out.

        Provenance must name the accepted branch. HEAD only coincides with it
        while the working tree happens to be on that branch.
        """
        return self.run(
            ["rev-parse", self.canonical_branch()], check=True
        ).stdout.strip()

    def ensure_canonical_checkout(self) -> None:
        """Put the working tree back on the accepted branch before mutating it.

        A crashed upload or a manual checkout can leave the canonical tree on
        another branch, and later commits would then land there. A clean tree is
        switched back. A tree with uncommitted changes is refused rather than
        carried across, because those changes belong to whatever was interrupted.
        """
        branch = self.canonical_branch()
        current = self.run(
            ["rev-parse", "--abbrev-ref", "HEAD"], check=True
        ).stdout.strip()
        if current == branch:
            return
        if self.run(["status", "--porcelain"], check=True).stdout.strip():
            raise WorkingTreeOffAcceptedBranchError(
                "The project working tree is on another branch with uncommitted "
                "changes; discard or synchronize them before continuing"
            )
        logger.warning("Returning a project working tree to its accepted branch")
        self.checkout(branch)

    def add_all(self) -> None:
        self.run(["add", "."], check=True)
        self._update_backup()

    def commit(self, message: str):
        self.run(["commit", "-m", message], check=True)
        self._update_backup()

    def push(self, branch: str | None = None):
        branch = branch or self.canonical_branch()
        self.run(["push", "origin", branch], check=True)
        self._update_backup()

    def get_commit_hash(self) -> str:
        return self.run(["rev-parse", "HEAD"]).stdout.strip()

    def get_tree_hash(self, revision: str = "HEAD") -> str:
        """Return the content identity of a revision, independent of commit metadata."""
        return self.run(
            ["rev-parse", "--verify", f"{revision}^{{tree}}"], check=True
        ).stdout.strip()

    def init_repo(self) -> None:
        """Initialize a repository with an application-owned commit identity.

        Server-side Git operations must not depend on a host or container's
        global Git configuration. Human attribution remains in the commit
        message and ELANORA audit records.
        """
        self.run(["init", "--initial-branch=main"], check=True)
        self.run(["config", "user.name", "ELANORA"], check=True)
        self.run(["config", "user.email", "system@elanora.local"], check=True)
        self._update_backup()

    def add_file(self, filepath: str):
        self.run(["add", filepath], check=True)
        self._update_backup()

    def merge(self, branch_name: str, message: str, no_ff: bool = True):
        args = ["merge", branch_name]
        if no_ff:
            args.append("--no-ff")
        args += ["-m", message]
        self.run(args, check=True)
        self._update_backup()

    def diff_stat(self, branch_name: str) -> str:
        return self.run(
            ["diff", f"{self.canonical_branch()}...{branch_name}", "--stat"]
        ).stdout

    def delete_branch_localy(self, branch_name: str):
        self.run(["branch", "-D", branch_name], check=False)

    def delete_branch_on_remote(self, branch_name: str):
        self.run(["push", "origin", "--delete", branch_name], check=False)

    def delete_branch(self, branch_name: str):
        self.delete_branch_localy(branch_name)
        self.delete_branch_on_remote(branch_name)
        update_backup(self.project_path.name, self.project_path.parent)

    def complete_pending_merge(
        self, branch_name: str, resolution_strategy: str = "auto"
    ) -> dict[str, Any]:
        """Prepare a merge in isolation, then publish it only if HEAD is unchanged."""
        allowed_strategies = {"auto", "accept_incoming", "accept_current"}
        if resolution_strategy not in allowed_strategies:
            raise ValueError("Unsupported merge resolution strategy")

        already_merged = self.run(
            [
                "merge-base",
                "--is-ancestor",
                branch_name,
                self.canonical_branch(),
            ],
            check=False,
        )
        if already_merged.returncode == 0:
            return {
                "branch_name": branch_name,
                "resolution_strategy": resolution_strategy,
                "status": "already_merged",
            }

        canonical_branch = self.canonical_branch()
        expected_head = self.run(
            ["rev-parse", canonical_branch], check=True
        ).stdout.strip()
        staging_root = Path(tempfile.mkdtemp(prefix="elanora-change-set-"))
        worktree = staging_root / "worktree"
        prepared_commit: str | None = None
        try:
            self.run(
                ["worktree", "add", "--detach", str(worktree), expected_head],
                check=True,
            )
            isolated = GitCommandRunner(worktree, maintain_backup=False)
            merge_result = isolated.run(
                ["merge", "--no-commit", "--no-ff", branch_name], check=False
            )
            conflicted_files = isolated.get_conflicted_files()
            if conflicted_files and resolution_strategy == "auto":
                raise ValueError("Contribution has conflicts that require resolution")
            if merge_result.returncode != 0 and not conflicted_files:
                raise RuntimeError("Git could not merge the contribution")
            if conflicted_files:
                checkout_side = (
                    "--theirs" if resolution_strategy == "accept_incoming" else "--ours"
                )
                isolated.run(["checkout", checkout_side, "--", "."], check=True)
            isolated.run(["add", "--all"], check=True)
            isolated.run(
                ["commit", "-m", f"Merge reviewed contribution {branch_name}"],
                check=True,
            )
            prepared_commit = isolated.get_commit_hash()

            current_head = self.run(
                ["rev-parse", canonical_branch], check=True
            ).stdout.strip()
            if current_head != expected_head:
                raise RuntimeError(
                    "Accepted project changed while the contribution was being prepared"
                )
            self.checkout(canonical_branch)
            self.run(["merge", "--ff-only", prepared_commit], check=True)
        finally:
            self.run(["worktree", "remove", "--force", str(worktree)], check=False)
            shutil.rmtree(staging_root, ignore_errors=True)

        if prepared_commit is None:
            raise RuntimeError("Contribution merge was not prepared")
        return {
            "branch_name": branch_name,
            "resolution_strategy": resolution_strategy,
            "status": "resolved",
        }

    def cleanup_on_error(self, branch_name: str | None = None):
        """Cleanup on error and return to the repository's accepted branch."""
        try:
            self.run(["checkout", self.canonical_branch()], check=False)
            if branch_name:
                self.run(["branch", "-D", branch_name], check=False)
            update_backup(self.project_path.name, self.project_path.parent)
        except Exception as error:
            logger.error(
                "Git cleanup failed; error_type=%s", safe_exception_type(error)
            )

    def detect_merge_conflicts(self) -> list[dict[str, str]]:
        result = self.run(["diff", "--name-only", "--diff-filter=U"])
        conflicts = []
        if result.stdout:
            for filename in result.stdout.strip().split("\n"):
                if filename.strip():
                    conflict_details = self.get_conflict_details(filename.strip())
                    conflicts.append(
                        {
                            "filename": filename.strip(),
                            "type": "content_conflict",
                            "details": conflict_details,
                        }
                    )
        return conflicts

    def get_current_branch(self) -> str:
        """Get the current branch name."""
        try:
            result = self.run(["branch", "--show-current"])
            return result.stdout.strip()
        except Exception:
            # Fallback method
            try:
                result = self.run(["rev-parse", "--abbrev-ref", "HEAD"])
                return result.stdout.strip()
            except Exception as error:
                logger.error(
                    "Unable to determine the current Git branch; error_type=%s",
                    safe_exception_type(error),
                )
                return "unknown"


def delete_project_folder(project_path: Path) -> None:
    """Delete a project folder without logging filesystem details."""
    if not project_path.exists():
        logger.warning("Project directory does not exist")
        return

    def on_rm_exc(func, path, exc_info):
        exc = (
            exc_info[1]
            if isinstance(exc_info, tuple) and len(exc_info) > 1
            else exc_info
        )
        # Try to remove read-only and retry
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
            logger.info("Deleted a read-only project entry after changing permissions")
            return
        except Exception as retry_error:
            logger.error(
                "Retrying project entry deletion failed; error_type=%s",
                safe_exception_type(retry_error),
            )
        logger.error(
            "Project entry deletion failed; error_type=%s",
            safe_exception_type(exc) if isinstance(exc, BaseException) else "Exception",
        )

    try:
        shutil.rmtree(project_path, onexc=on_rm_exc)
        logger.info("Deleted the project directory")

    except Exception as fs_exc:
        logger.error(
            "Failed to delete the project directory; error_type=%s",
            safe_exception_type(fs_exc),
        )
        raise RuntimeError("Failed to delete project directory") from fs_exc
