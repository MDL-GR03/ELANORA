"""Prepare safe, researcher-facing comparisons of EAF files in Git revisions."""

import subprocess
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from shutil import which

from app.elan import EafComparison, compare_eaf, parse_eaf
from app.storage.paths import safe_project_path


class EafReviewUnavailableError(ValueError):
    """The requested versions cannot be presented as a semantic EAF review."""


def _validated_repository_filename(filename: str) -> str:
    path = PurePosixPath(filename)
    if (
        path.is_absolute()
        or ".." in path.parts
        or not path.parts
        or path.suffix.lower() != ".eaf"
    ):
        raise EafReviewUnavailableError(
            "Only project-relative EAF files can be reviewed"
        )
    return path.as_posix()


def _git(
    project_path: Path, arguments: list[str]
) -> subprocess.CompletedProcess[bytes]:
    # Arguments are passed without a shell; revision and path components are
    # validated before this boundary. Git must be resolved from the runtime PATH.
    git_executable = which("git")
    if git_executable is None:
        raise EafReviewUnavailableError("Git is not available on this server")
    return subprocess.run(  # noqa: S603
        [
            git_executable,
            "-c",
            f"safe.directory={project_path.resolve()}",
            "-c",
            "core.quotepath=false",
            *arguments,
        ],
        cwd=project_path,
        capture_output=True,
        check=False,
    )


def _read_blob(project_path: Path, revision: str, filename: str) -> bytes:
    verified = _git(
        project_path,
        ["rev-parse", "--verify", "--quiet", "--end-of-options", revision],
    )
    if verified.returncode != 0:
        raise EafReviewUnavailableError("The requested contribution no longer exists")
    result = _git(project_path, ["show", f"{revision}:{filename}"])
    if result.returncode != 0:
        raise EafReviewUnavailableError(
            "This EAF file is not present in one of the compared versions"
        )
    return result.stdout


def _canonical_revision(project_path: Path) -> str:
    for branch in ("main", "master"):
        revision = f"refs/heads/{branch}"
        if (
            _git(
                project_path,
                ["show-ref", "--verify", "--quiet", revision],
            ).returncode
            == 0
        ):
            return revision
    raise EafReviewUnavailableError("Project has no accepted branch")


def compare_repository_eaf(
    projects_root: Path,
    project_name: str,
    branch_name: str,
    filename: str,
) -> EafComparison:
    """Compare the accepted EAF with a contribution without changing the checkout."""
    safe_filename = _validated_repository_filename(filename)
    project_path = safe_project_path(projects_root, project_name)
    if not project_path.is_dir():
        raise FileNotFoundError("Project repository not found")
    before = parse_eaf(
        _read_blob(project_path, _canonical_revision(project_path), safe_filename)
    )
    after = parse_eaf(
        _read_blob(project_path, f"refs/heads/{branch_name}", safe_filename)
    )
    return compare_eaf(before, after)


def validate_repository_eafs(project_path: Path, branch_name: str) -> dict[str, bytes]:
    """Validate and return every EAF in the exact submitted Git tree."""
    revision = f"refs/heads/{branch_name}"
    listing = _git(project_path, ["ls-tree", "-r", "--name-only", revision])
    if listing.returncode != 0:
        raise EafReviewUnavailableError("The requested contribution no longer exists")
    filenames = [
        line.decode("utf-8")
        for line in listing.stdout.splitlines()
        if line.lower().endswith(b".eaf")
    ]
    contents = {
        filename: _read_blob(project_path, revision, filename) for filename in filenames
    }
    for content in contents.values():
        parse_eaf(content)
    return contents


def comparison_payload(comparison: EafComparison) -> dict[str, object]:
    """Convert the immutable domain result into an API-ready object."""
    return asdict(comparison)
