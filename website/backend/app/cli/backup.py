"""Take, list and verify ELANORA's encrypted off-host backups."""

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from app.core.settings import get_settings
from app.service.offsite_backup import (
    BackupError,
    create_offsite_backup,
    dump_with_pg_dump,
    list_backups,
    prune_backups,
    verify_latest_backup,
)
from app.storage.assets import get_backup_storage

PASSPHRASE_ENV = "ELANORA_BACKUP_PASSPHRASE"  # noqa: S105 - variable name


def _passphrase() -> str:
    value = os.environ.get(PASSPHRASE_ENV, "")
    if not value:
        raise SystemExit(f"{PASSPHRASE_ENV} must be set")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create", help="take tonight's backup and prune old copies")
    commands.add_parser("list", help="list stored backups, oldest first")
    commands.add_parser("verify", help="read the newest backup back and check it")
    return parser


def _create() -> dict[str, object]:
    settings = get_settings()
    database_url = settings.resolved_database_url.replace("+asyncpg", "")
    report = create_offsite_backup(
        storage=get_backup_storage(),
        projects=Path(settings.elan_projects_base_path),
        assets=Path(settings.instance_assets_base_path),
        passphrase=_passphrase(),
        dump_database=dump_with_pg_dump(database_url),
    )
    removed = prune_backups(get_backup_storage(), keep=settings.backup_retain_copies)
    return {**asdict(report), "removed": removed}


def main() -> None:
    """Run one backup command, reporting the result as JSON."""
    arguments = _parser().parse_args()
    try:
        if arguments.command == "create":
            result: dict[str, object] = _create()
        elif arguments.command == "list":
            result = {"backups": list_backups(get_backup_storage())}
        else:
            result = asdict(verify_latest_backup(get_backup_storage(), _passphrase()))
    except BackupError as error:
        raise SystemExit(str(error)) from error
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
