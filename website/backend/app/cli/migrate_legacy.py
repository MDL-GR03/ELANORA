"""Import the reviewed MySQL-era dataset into an empty PostgreSQL database."""

import argparse
import asyncio
import json
from dataclasses import asdict
from pathlib import Path

from app.db.database import close_database, get_session_maker, init_database
from app.legacy_migration.dump_parser import verify_dump
from app.legacy_migration.service import migrate_legacy_database
from app.utils.file_processing import get_elanora_projects_base_path


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", type=Path, required=True)
    parser.add_argument("--source-files", type=Path, required=True)
    parser.add_argument(
        "--projects-root",
        type=Path,
        default=Path(get_elanora_projects_base_path()),
    )
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    dump_path = arguments.dump.resolve(strict=True)
    source_files = arguments.source_files.resolve(strict=True)
    projects_root = arguments.projects_root.resolve()
    verify_dump(dump_path)

    init_database()
    try:
        async with get_session_maker()() as db:
            report = await migrate_legacy_database(
                db,
                dump_path=dump_path,
                source_files=source_files,
                projects_root=projects_root,
            )
    finally:
        await close_database()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


def main() -> None:
    """Run the guarded one-way legacy import."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
