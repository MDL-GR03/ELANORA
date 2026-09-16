"""Merging a reviewed contribution into the accepted project."""

from pathlib import Path

from app.core.centralized_logging import get_logger

logger = get_logger()


class GitMerger:
    """Handles Git merge operations."""

    def __init__(self, project_path: Path):
        """Initialize with the project path."""
        self.project_path = project_path
