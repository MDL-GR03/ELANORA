import hashlib
import json
import uuid
from pathlib import Path

import pytest

from app.storage.sync_evidence import SyncEvidenceStore


def test_preserve_copies_content_and_records_hashes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    evidence = tmp_path / "evidence"
    source = project / "elan_files/session.eaf"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"validated-source")
    operation_id = uuid.uuid4()

    key, manifest = SyncEvidenceStore(evidence).preserve(
        operation_id,
        project,
        [
            {"filename": "elan_files/session.eaf", "status": "modified"},
            {"filename": "elan_files/deleted.eaf", "status": "deleted"},
        ],
    )

    assert key == str(operation_id)
    assert (
        evidence / key / "elan_files/session.eaf"
    ).read_bytes() == b"validated-source"
    assert manifest[0]["sha256"] == hashlib.sha256(b"validated-source").hexdigest()
    assert manifest[1] == {"filename": "elan_files/deleted.eaf", "status": "deleted"}
    assert json.loads((evidence / key / "manifest.json").read_text()) == manifest


def test_preserve_rejects_paths_outside_project(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()

    with pytest.raises(ValueError, match="escapes project"):
        SyncEvidenceStore(tmp_path / "evidence").preserve(
            uuid.uuid4(), project, [{"filename": "../secret.eaf", "status": "added"}]
        )


def test_discard_only_removes_the_requested_operation(tmp_path: Path) -> None:
    store = SyncEvidenceStore(tmp_path / "evidence")
    first = uuid.uuid4()
    second = uuid.uuid4()
    (store.root / str(first)).mkdir(parents=True)
    (store.root / str(second)).mkdir()

    store.discard(str(first))

    assert not (store.root / str(first)).exists()
    assert (store.root / str(second)).exists()
