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


def _read_optional_blob(
    project_path: Path, revision: str, filename: str
) -> bytes | None:
    result = _git(project_path, ["show", f"{revision}:{filename}"])
    return result.stdout if result.returncode == 0 else None


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
    *,
    accepted_revision: str | None = None,
) -> EafComparison:
    """Compare the accepted EAF with a contribution without changing the checkout."""
    safe_filename = _validated_repository_filename(filename)
    project_path = safe_project_path(projects_root, project_name)
    if not project_path.is_dir():
        raise FileNotFoundError("Project repository not found")
    canonical_revision = accepted_revision or _canonical_revision(project_path)
    submitted_revision = f"refs/heads/{branch_name}"
    if (
        _git(
            project_path,
            [
                "rev-parse",
                "--verify",
                "--quiet",
                "--end-of-options",
                submitted_revision,
            ],
        ).returncode
        != 0
    ):
        raise EafReviewUnavailableError("The requested contribution no longer exists")
    before_blob = _read_optional_blob(project_path, canonical_revision, safe_filename)
    after_blob = _read_optional_blob(project_path, submitted_revision, safe_filename)
    if before_blob is None and after_blob is None:
        raise EafReviewUnavailableError(
            "This EAF file is not present in either compared version"
        )
    before = parse_eaf(before_blob) if before_blob is not None else None
    after = parse_eaf(after_blob) if after_blob is not None else None
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
