"""Safe filesystem path construction for researcher-controlled names."""

import unicodedata
from pathlib import Path


def safe_project_path(base_directory: Path, project_name: str) -> Path:
    """Return a project directory guaranteed to remain below its storage root."""
    normalized = unicodedata.normalize("NFC", project_name).strip()
    if not normalized or normalized in {".", ".."}:
        raise ValueError("Project name must not be empty or relative")
    if any(character in normalized for character in ("/", "\\", "\x00")):
        raise ValueError("Project name must not contain path separators")
    if any(unicodedata.category(character).startswith("C") for character in normalized):
        raise ValueError("Project name must not contain control characters")

    root = base_directory.resolve()
    candidate = (root / normalized).resolve()
    if candidate.parent != root:
        raise ValueError("Project path escapes the configured storage root")
    return candidate
