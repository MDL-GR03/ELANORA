"""Scan accepted project integrity without modifying project data."""

import argparse
import asyncio
import json

from app.db.database import close_database, get_session_maker, init_database
from app.service.git import GitService


async def check_integrity(project_name: str | None = None) -> int:
    """Run one persisted integrity scan and return a process exit status."""
    init_database()
    session_maker = get_session_maker()
    async with session_maker() as db:
        service = GitService()
        results = (
            [await service.record_current_revision_health(project_name, db)]
            if project_name
            else await service.scan_all_project_integrity(db)
        )
    print(json.dumps(results, indent=2, sort_keys=True))
    return 0 if all(item["status"] == "healthy" for item in results) else 1


async def _run(project_name: str | None) -> int:
    try:
        return await check_integrity(project_name)
    finally:
        await close_database()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check immutable accepted revisions against disk and database."
    )
    parser.add_argument("--project", help="Only scan this project name")
    arguments = parser.parse_args()
    raise SystemExit(asyncio.run(_run(arguments.project)))


if __name__ == "__main__":
    main()
