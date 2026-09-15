"""Nightly off-host backups, and proving a copy can still be restored.

The institution accepts losing at most a day's work and restoring within one
day. That needs a backup taken every night, kept somewhere the installation
cannot destroy, and verified rather than assumed.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.recovery.bundle import extract_bundle
from app.service.offsite_backup import (
    BACKUP_PREFIX,
    BackupError,
    create_offsite_backup,
    list_backups,
    prune_backups,
    verify_latest_backup,
)

PASSPHRASE = "drill-passphrase-only"  # noqa: S105 - test credential


class FakeBackupStorage:
    """An off-host store that refuses to overwrite an existing backup."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, content: bytes) -> None:
        if key in self.objects:
            raise ValueError(f"{key} already exists")
        self.objects[key] = content

    def read(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)

    def list_keys(self, prefix: str) -> list[str]:
        return sorted(key for key in self.objects if key.startswith(prefix))


@pytest.fixture
def installation(tmp_path: Path) -> dict[str, Path]:
    projects = tmp_path / "projects" / "corpus"
    projects.mkdir(parents=True)
    (projects / "session.eaf").write_bytes(b"<ANNOTATION_DOCUMENT/>")
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "logo.webp").write_bytes(b"logo")
    return {"projects": tmp_path / "projects", "assets": assets}


def _dump(content: bytes = b"-- database dump\n"):
    def dump(destination: Path) -> None:
        destination.write_bytes(content)

    return dump


def test_a_backup_is_encrypted_named_by_its_moment_and_restorable(
    installation: dict[str, Path], tmp_path: Path
) -> None:
    storage = FakeBackupStorage()

    report = create_offsite_backup(
        storage=storage,
        projects=installation["projects"],
        assets=installation["assets"],
        passphrase=PASSPHRASE,
        dump_database=_dump(),
        now=datetime(2026, 9, 16, 2, 0, tzinfo=UTC),
    )

    assert report.key == f"{BACKUP_PREFIX}/elanora-20260916T020000Z.elanora"
    assert report.size_bytes > 0
    assert b"session.eaf" not in storage.objects[report.key], "must be encrypted"
    restored = tmp_path / "restored"
    (tmp_path / "copy.elanora").write_bytes(storage.objects[report.key])
    manifest = extract_bundle(tmp_path / "copy.elanora", restored, PASSPHRASE)
    assert manifest["format"] == "elanora-recovery-v1"
    assert (restored / "projects" / "corpus" / "session.eaf").read_bytes() == (
        b"<ANNOTATION_DOCUMENT/>"
    )
    assert (restored / "database.sql").read_bytes() == b"-- database dump\n"


def test_two_backups_in_one_second_do_not_overwrite_each_other(
    installation: dict[str, Path],
) -> None:
    storage = FakeBackupStorage()
    moment = datetime(2026, 9, 16, 2, 0, tzinfo=UTC)
    arguments = {
        "storage": storage,
        "projects": installation["projects"],
        "assets": installation["assets"],
        "passphrase": PASSPHRASE,
        "dump_database": _dump(),
        "now": moment,
    }

    create_offsite_backup(**arguments)
    with pytest.raises(BackupError, match="already exists"):
        create_offsite_backup(**arguments)

    assert len(storage.objects) == 1


def test_older_copies_are_pruned_and_the_newest_are_kept(
    installation: dict[str, Path],
) -> None:
    storage = FakeBackupStorage()
    for day in range(1, 6):
        create_offsite_backup(
            storage=storage,
            projects=installation["projects"],
            assets=installation["assets"],
            passphrase=PASSPHRASE,
            dump_database=_dump(),
            now=datetime(2026, 9, day, 2, 0, tzinfo=UTC),
        )

    removed = prune_backups(storage, keep=2)

    assert len(removed) == 3
    assert [key.rsplit("-", 1)[-1] for key in list_backups(storage)] == [
        "20260904T020000Z.elanora",
        "20260905T020000Z.elanora",
    ]


def test_verifying_the_latest_backup_reads_it_back_from_the_store(
    installation: dict[str, Path],
) -> None:
    storage = FakeBackupStorage()
    create_offsite_backup(
        storage=storage,
        projects=installation["projects"],
        assets=installation["assets"],
        passphrase=PASSPHRASE,
        dump_database=_dump(),
        now=datetime(2026, 9, 16, 2, 0, tzinfo=UTC),
    )

    report = verify_latest_backup(storage, PASSPHRASE)

    assert report.key.endswith("20260916T020000Z.elanora")
    assert report.files, "the manifest lists what a restore would return"


def test_a_corrupted_backup_is_reported_rather_than_trusted(
    installation: dict[str, Path],
) -> None:
    storage = FakeBackupStorage()
    report = create_offsite_backup(
        storage=storage,
        projects=installation["projects"],
        assets=installation["assets"],
        passphrase=PASSPHRASE,
        dump_database=_dump(),
        now=datetime(2026, 9, 16, 2, 0, tzinfo=UTC),
    )
    damaged = bytearray(storage.objects[report.key])
    damaged[-1] ^= 0xFF
    storage.objects[report.key] = bytes(damaged)

    with pytest.raises(BackupError, match="could not be verified"):
        verify_latest_backup(storage, PASSPHRASE)


def test_verifying_without_any_backup_says_so(installation: dict[str, Path]) -> None:
    with pytest.raises(BackupError, match="no backup"):
        verify_latest_backup(FakeBackupStorage(), PASSPHRASE)


def test_a_failed_database_dump_stores_nothing(
    installation: dict[str, Path],
) -> None:
    storage = FakeBackupStorage()

    def refuse(_destination: Path) -> None:
        raise RuntimeError("pg_dump exited with status 1")

    with pytest.raises(BackupError, match="database dump"):
        create_offsite_backup(
            storage=storage,
            projects=installation["projects"],
            assets=installation["assets"],
            passphrase=PASSPHRASE,
            dump_database=refuse,
            now=datetime(2026, 9, 16, 2, 0, tzinfo=UTC),
        )

    assert storage.objects == {}
