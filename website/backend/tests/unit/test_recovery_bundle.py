"""Encrypted disaster-recovery bundle guarantees."""

from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

from app.recovery.bundle import create_bundle, extract_bundle, verify_bundle

PASSPHRASE = "correct horse battery staple"  # noqa: S105 - inert fixture


def _sources(root: Path) -> tuple[Path, Path, Path]:
    root.mkdir(parents=True)
    dump = root / "database.sql"
    projects = root / "projects"
    assets = root / "assets"
    dump.write_text("CREATE TABLE example (id integer);", encoding="utf-8")
    (projects / "Corpus" / ".git").mkdir(parents=True)
    (projects / "Corpus" / "elan_files").mkdir()
    (projects / "Corpus" / ".git" / "HEAD").write_text(
        "ref: refs/heads/master\n", encoding="utf-8"
    )
    (projects / "Corpus" / "elan_files" / "session.eaf").write_bytes(
        b"<ANNOTATION_DOCUMENT/>"
    )
    assets.mkdir()
    (assets / "institution-logo.png").write_bytes(b"PNG fixture")
    return dump, projects, assets


def test_encrypted_bundle_round_trip_preserves_all_sources(tmp_path: Path) -> None:
    dump, projects, assets = _sources(tmp_path / "source")
    bundle = tmp_path / "backup.elanora"
    manifest = create_bundle(dump, projects, assets, bundle, PASSPHRASE)

    with pytest.raises(FileExistsError):
        create_bundle(dump, projects, assets, bundle, PASSPHRASE)

    assert bundle.read_bytes()[:8] != b"database"
    assert verify_bundle(bundle, PASSPHRASE)["files"] == manifest["files"]
    destination = tmp_path / "restored"
    extract_bundle(bundle, destination, PASSPHRASE)

    assert (destination / "database.sql").read_bytes() == dump.read_bytes()
    assert (
        destination / "projects" / "Corpus" / "elan_files" / "session.eaf"
    ).read_bytes() == b"<ANNOTATION_DOCUMENT/>"
    assert (
        destination / "instance-assets" / "institution-logo.png"
    ).read_bytes() == b"PNG fixture"


def test_bundle_rejects_wrong_key_tampering_and_existing_destination(
    tmp_path: Path,
) -> None:
    dump, projects, assets = _sources(tmp_path / "source")
    bundle = tmp_path / "backup.elanora"
    create_bundle(dump, projects, assets, bundle, PASSPHRASE)

    with pytest.raises(InvalidTag):
        verify_bundle(bundle, "this passphrase is wrong")
    content = bytearray(bundle.read_bytes())
    content[len(content) // 2] ^= 1
    bundle.write_bytes(content)
    with pytest.raises(InvalidTag):
        verify_bundle(bundle, PASSPHRASE)

    clean_bundle = tmp_path / "clean.elanora"
    create_bundle(dump, projects, assets, clean_bundle, PASSPHRASE)
    destination = tmp_path / "existing"
    destination.mkdir()
    with pytest.raises(FileExistsError):
        extract_bundle(clean_bundle, destination, PASSPHRASE)


def test_bundle_rejects_short_passphrase_and_source_symlink(tmp_path: Path) -> None:
    dump, projects, assets = _sources(tmp_path / "source")
    with pytest.raises(ValueError, match="at least 16"):
        create_bundle(dump, projects, assets, tmp_path / "short", "too short")
    (projects / "linked").symlink_to(dump)
    with pytest.raises(ValueError, match="symbolic link"):
        create_bundle(dump, projects, assets, tmp_path / "linked", PASSPHRASE)
