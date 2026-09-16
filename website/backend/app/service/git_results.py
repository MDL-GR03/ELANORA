"""What a Git operation reports back to the workflow that asked for it."""

from dataclasses import dataclass


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
