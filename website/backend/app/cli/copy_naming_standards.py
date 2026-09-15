"""Copy each project's upload naming standard into a protocol draft for review."""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.db.database import close_database, get_session_maker, init_database
from app.service.naming_standard_migration import (
    copy_naming_standards_into_protocol_drafts,
)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what would be copied without writing anything",
    )
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    init_database()
    try:
        async with get_session_maker()() as db:
            report = await copy_naming_standards_into_protocol_drafts(
                db, dry_run=arguments.dry_run
            )
            if arguments.dry_run:
                await db.rollback()
            else:
                await db.commit()
    finally:
        await close_database()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


def main() -> None:
    """Run the idempotent copy of naming standards into protocol drafts."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
