"""Tests for filesystem containment boundaries."""

from pathlib import Path

import pytest

from app.storage.paths import safe_project_path


def test_project_path_is_normalized_below_root(tmp_path: Path) -> None:
    """Preserve a human-readable name while keeping it below the root."""
    assert safe_project_path(tmp_path, "  Corpus 2026  ") == tmp_path / "Corpus 2026"


@pytest.mark.parametrize(
    "name",
    [
        "",
        ".",
        "..",
        "../escape",
        "folder/project",
        "folder\\project",
        "bad\x00name",
        "bad\nname",
    ],
)
def test_unsafe_project_names_are_rejected(tmp_path: Path, name: str) -> None:
    """Reject traversal, separators, NUL bytes, and control characters."""
    with pytest.raises(ValueError):
        safe_project_path(tmp_path, name)
