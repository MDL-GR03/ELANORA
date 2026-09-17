"""File processing utilities for ELAN files."""

from pathlib import Path

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_PROJECTS_BASE_PATH

logger = get_logger()


def get_elanora_projects_base_path() -> str:
    """Get the base path for elanora_projects directory."""
    try:
        configured_path = ELAN_PROJECTS_BASE_PATH
        logger.debug("Using the configured ELAN project storage root")

        # If it's a relative path, make it relative to the repo root
        if not Path(configured_path).is_absolute():
            # Navigate up from current file to repo root
            current_dir = Path(__file__).resolve()
            # file_processing.py -> utils -> app -> backend -> website -> repo_root
            repo_root = current_dir.parent.parent.parent.parent.parent
            base_path = str(repo_root / configured_path)
            logger.debug("Resolved the relative ELAN project storage root")
            return base_path
        else:
            # It's already an absolute path
            return configured_path

    except ImportError:
        # Fallback to calculated path
        current_dir = Path(__file__).resolve()
        # Navigate up: file_processing.py -> utils -> app -> backend -> website -> repo_root
        repo_root = current_dir.parent.parent.parent.parent.parent
        base_path = str(repo_root / "elanora_projects")
        logger.debug("Calculated the fallback ELAN project storage root")
        return base_path


def make_path_relative_to_projects(absolute_path: str) -> str:
    """Convert absolute path to relative path from elanora_projects directory."""
    base_path = get_elanora_projects_base_path()
    abs_path = Path(absolute_path).resolve()
    base = Path(base_path).resolve()

    logger.debug("Converting an ELAN project path to its storage-relative form")

    try:
        relative_path = abs_path.relative_to(base)
        result = str(relative_path).replace(
            "\\", "/"
        )  # Use forward slashes for consistency
        logger.debug("Converted an ELAN project path to storage-relative form")
        return result
    except ValueError:
        # Path is not under elanora_projects, return as-is but log warning
        logger.warning("Path is outside the configured ELAN project storage root")
        return absolute_path


def make_path_absolute_from_projects(relative_path: str) -> str:
    """Convert relative path from elanora_projects to absolute path."""
    base_path = get_elanora_projects_base_path()
    return str(Path(base_path) / relative_path)


class ElanFileProcessor:
    """Utilities for processing ELAN XML files."""

    @staticmethod
    def validate_elan_file(file_path: str) -> Path:
        """Validate and return Path object for ELAN file."""
        file_path_obj = Path(file_path)
        logger.info("Validating an ELAN file")
        if not file_path_obj.exists():
            logger.error("ELAN file validation failed: file not found")
            raise FileNotFoundError(f"ELAN file not found: {file_path}")
        if file_path_obj.suffix.lower() != ".eaf":
            logger.error("ELAN file validation failed: unsupported extension")
            raise ValueError(f"Not an ELAN file: {file_path}")
        logger.debug("ELAN file path validation passed")
        return file_path_obj
