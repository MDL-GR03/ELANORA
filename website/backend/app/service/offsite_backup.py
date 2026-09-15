"""Nightly encrypted backups kept off the installation's own host.

The institution accepts losing at most a day of work and restoring within one
day. That is met by taking one encrypted, checksum-manifested snapshot of the
database, project storage and instance assets every night, writing it to a
store the installation itself cannot overwrite, keeping a rolling set of
copies, and verifying the newest one rather than assuming it is good.

Backups are named by the moment they were taken, so an accidental second run
in the same second is refused instead of replacing a good copy.
"""

import shutil
import subprocess
import tempfile
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.recovery.bundle import create_bundle, verify_bundle

logger = get_logger()

BACKUP_PREFIX = "backups"
BACKUP_SUFFIX = ".elanora"
DUMP_TIMEOUT_SECONDS = 3600


class BackupError(RuntimeError):
    """A backup could not be taken, listed or verified."""


class BackupStorage(Protocol):
    """Somewhere durable that the installation does not control."""

    def put(self, key: str, content: bytes) -> None: ...
    def read(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def list_keys(self, prefix: str) -> list[str]: ...


@dataclass(frozen=True)
class BackupReport:
    """One stored backup."""

    key: str
    size_bytes: int
    created_at: str
    files: tuple[str, ...]


def backup_key(now: datetime) -> str:
    """The object key for a backup taken at this moment."""
    stamp = now.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")
    return f"{BACKUP_PREFIX}/elanora-{stamp}{BACKUP_SUFFIX}"


def list_backups(storage: BackupStorage) -> list[str]:
    """Stored backups, oldest first: their names sort by the moment taken."""
    return sorted(
        key
        for key in storage.list_keys(f"{BACKUP_PREFIX}/")
        if key.endswith(BACKUP_SUFFIX)
    )


def create_offsite_backup(
    *,
    storage: BackupStorage,
    projects: Path,
    assets: Path,
    passphrase: str,
    dump_database: Callable[[Path], None],
    now: datetime | None = None,
) -> BackupReport:
    """Take one encrypted snapshot and store it off-host.

    Nothing is stored unless the database dump, the bundle and its own
    verification all succeed.
    """
    moment = now or datetime.now(UTC)
    key = backup_key(moment)
    if key in set(list_backups(storage)):
        raise BackupError(f"A backup for this moment already exists: {key}")
    with tempfile.TemporaryDirectory(prefix="elanora-backup-") as workspace:
        root = Path(workspace)
        dump = root / "database.sql"
        try:
            dump_database(dump)
        except Exception as error:
            raise BackupError(
                f"The database dump failed: {safe_exception_type(error)}"
            ) from error
        bundle = root / "backup.elanora"
        try:
            manifest = create_bundle(dump, projects, assets, bundle, passphrase)
        except Exception as error:
            raise BackupError(
                f"The backup could not be created: {safe_exception_type(error)}"
            ) from error
        content = bundle.read_bytes()
    try:
        storage.put(key, content)
    except Exception as error:
        raise BackupError(f"The backup could not be stored: {error}") from error
    logger.info("Stored an encrypted off-host backup")
    return BackupReport(
        key=key,
        size_bytes=len(content),
        created_at=str(manifest["created_at"]),
        files=_manifest_paths(manifest),
    )


def prune_backups(storage: BackupStorage, *, keep: int) -> list[str]:
    """Remove all but the newest ``keep`` backups, returning what was removed."""
    if keep < 1:
        raise BackupError("At least one backup must be kept")
    stored = list_backups(storage)
    removable = stored[: max(0, len(stored) - keep)]
    for key in removable:
        storage.delete(key)
    if removable:
        logger.info("Removed %s backup(s) beyond the retained set", len(removable))
    return removable


def verify_latest_backup(storage: BackupStorage, passphrase: str) -> BackupReport:
    """Read the newest backup back and check it against its own manifest."""
    stored = list_backups(storage)
    if not stored:
        raise BackupError("There is no backup to verify")
    key = stored[-1]
    content = storage.read(key)
    with tempfile.TemporaryDirectory(prefix="elanora-verify-") as workspace:
        copy = Path(workspace) / "backup.elanora"
        copy.write_bytes(content)
        try:
            manifest = verify_bundle(copy, passphrase)
        except Exception as error:
            raise BackupError(
                f"The newest backup could not be verified: {safe_exception_type(error)}"
            ) from error
    logger.info("Verified the newest off-host backup")
    return BackupReport(
        key=key,
        size_bytes=len(content),
        created_at=str(manifest["created_at"]),
        files=_manifest_paths(manifest),
    )


def dump_with_pg_dump(database_url: str) -> Callable[[Path], None]:
    """Dump the database with pg_dump, found on PATH and run without a shell."""
    program = shutil.which("pg_dump")
    if program is None:
        raise BackupError("pg_dump is not installed on this host")

    def dump(destination: Path) -> None:
        with destination.open("wb") as target:
            completed = subprocess.run(  # noqa: S603 - fixed argument list
                [
                    program,
                    "--no-owner",
                    "--no-privileges",
                    "--serializable-deferrable",
                    "--dbname",
                    database_url,
                ],
                stdout=target,
                stderr=subprocess.PIPE,
                timeout=DUMP_TIMEOUT_SECONDS,
                check=False,
            )
        if completed.returncode != 0:
            raise RuntimeError("pg_dump did not complete")

    return dump


def _manifest_paths(manifest: dict[str, object]) -> tuple[str, ...]:
    files = manifest.get("files")
    if not isinstance(files, Sequence):
        return ()
    return tuple(
        str(item["path"]) for item in files if isinstance(item, dict) and "path" in item
    )
