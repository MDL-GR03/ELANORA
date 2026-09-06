from pathlib import Path

import pytest

from app.elan.validation import EafValidationError
from app.schema.common.git import FileStatus
from app.service.git import GitService


def changed_file(filename: str, status: str = "modified") -> FileStatus:
    return FileStatus(filename=filename, status=status, description="server edit")


def test_server_sync_preflight_accepts_a_complete_valid_eaf(tmp_path: Path) -> None:
    elan_directory = tmp_path / "elan_files"
    elan_directory.mkdir()
    fixture = Path(__file__).parents[1] / "fixtures/eaf/complete-valid.eaf"
    (elan_directory / "complete-valid.eaf").write_bytes(fixture.read_bytes())

    GitService._validate_sync_candidates(
        tmp_path, [changed_file("elan_files/complete-valid.eaf")]
    )


def test_server_sync_preflight_rejects_invalid_eaf_before_staging(
    tmp_path: Path,
) -> None:
    elan_directory = tmp_path / "elan_files"
    elan_directory.mkdir()
    (elan_directory / "broken.eaf").write_text("<ANNOTATION_DOCUMENT>")

    with pytest.raises(EafValidationError):
        GitService._validate_sync_candidates(
            tmp_path, [changed_file("elan_files/broken.eaf")]
        )


def test_server_sync_preflight_allows_a_recorded_deletion(tmp_path: Path) -> None:
    GitService._validate_sync_candidates(
        tmp_path, [changed_file("elan_files/deleted.eaf", "deleted")]
    )
