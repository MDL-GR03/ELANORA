"""Running Git commands against one project, and keeping its backup current."""

import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.service import git_backup
from app.service.git_results import MergeReadiness

logger = get_logger()


class WorkingTreeOffAcceptedBranchError(RuntimeError):
    """The canonical working tree is off its accepted branch with local changes."""


class GitCommandRunner:
    """Runs generic git commands and returns results."""

    def __init__(self, project_path: Path, *, maintain_backup: bool = True) -> None:
        self.project_path = project_path
        self.maintain_backup = maintain_backup

    def _update_backup(self) -> None:
        if self.maintain_backup:
            git_backup.update_backup(self.project_path.name, self.project_path.parent)

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

    def get_conflicted_files(self) -> list[str]:
        result = self.run(["diff", "--name-only", "--diff-filter=U"])
        return [
            line.strip() for line in result.stdout.strip().split("\n") if line.strip()
        ]

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

    def merge(self, branch_name: str, message: str, no_ff: bool = True):
        args = ["merge", branch_name]
        if no_ff:
            args.append("--no-ff")
        args += ["-m", message]
        self.run(args, check=True)
        self._update_backup()

    def delete_branch_localy(self, branch_name: str):
        self.run(["branch", "-D", branch_name], check=False)

    def delete_branch_on_remote(self, branch_name: str):
        self.run(["push", "origin", "--delete", branch_name], check=False)

    def delete_branch(self, branch_name: str):
        self.delete_branch_localy(branch_name)
        self.delete_branch_on_remote(branch_name)
        git_backup.update_backup(self.project_path.name, self.project_path.parent)

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
