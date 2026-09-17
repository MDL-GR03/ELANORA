"""Reading `git diff --name-status` output."""

from dataclasses import dataclass, field

from app.core.centralized_logging import get_logger

logger = get_logger()
NAME_STATUS_FIELD_COUNT = 2


@dataclass(slots=True)
class NameStatusChanges:
    """Files a branch adds, modifies and deletes relative to its base."""

    new_files: list[str] = field(default_factory=list)
    modified_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)


def parse_name_status(output: str) -> NameStatusChanges:
    """Sort `git diff --name-status` lines into added, modified and deleted files."""
    changes = NameStatusChanges()
    targets = {
        "A": changes.new_files,
        "M": changes.modified_files,
        "D": changes.deleted_files,
    }
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        parts = stripped.split("\t", 1)
        if len(parts) != NAME_STATUS_FIELD_COUNT:
            logger.warning("Skipped an unexpected git name-status line")
            continue
        status, filename = parts
        target = targets.get(status)
        if target is None:
            logger.warning("Skipped an unknown git status %s", status)
            continue
        target.append(filename)
    return changes
