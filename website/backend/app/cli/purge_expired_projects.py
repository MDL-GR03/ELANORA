"""Purge the content of deleted projects whose retention period has ended."""

import argparse
import asyncio
import json
from dataclasses import asdict

from app.db.database import close_database, get_session_maker, init_database
from app.service.retention_purge import purge_expired_projects


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report what is due without destroying anything",
    )
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    init_database()
    try:
        async with get_session_maker()() as db:
            report = await purge_expired_projects(db, dry_run=arguments.dry_run)
            if arguments.dry_run:
                await db.rollback()
            else:
                await db.commit()
    finally:
        await close_database()
    print(json.dumps(asdict(report), indent=2, sort_keys=True))


def main() -> None:
    """Run the retention purge."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
