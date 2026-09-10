"""Create, verify, or extract encrypted ELANORA recovery bundles."""

import argparse
import json
import os
from pathlib import Path

from app.recovery.bundle import create_bundle, extract_bundle, verify_bundle

PASSPHRASE_ENV = "ELANORA_BACKUP_PASSPHRASE"  # noqa: S105 - variable name


def _passphrase() -> str:
    value = os.environ.get(PASSPHRASE_ENV, "")
    if not value:
        raise SystemExit(f"{PASSPHRASE_ENV} must be set")
    return value


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage encrypted, checksum-verified ELANORA recovery bundles."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create")
    create.add_argument("--database-dump", type=Path, required=True)
    create.add_argument("--projects", type=Path, required=True)
    create.add_argument("--assets", type=Path, required=True)
    create.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("bundle", type=Path)
    extract = commands.add_parser("extract")
    extract.add_argument("bundle", type=Path)
    extract.add_argument("--destination", type=Path, required=True)
    return parser


def main() -> None:
    arguments = _parser().parse_args()
    passphrase = _passphrase()
    if arguments.command == "create":
        manifest = create_bundle(
            arguments.database_dump,
            arguments.projects,
            arguments.assets,
            arguments.output,
            passphrase,
        )
    elif arguments.command == "verify":
        manifest = verify_bundle(arguments.bundle, passphrase)
    else:
        manifest = extract_bundle(arguments.bundle, arguments.destination, passphrase)
    print(json.dumps(manifest, indent=2, sort_keys=True))
