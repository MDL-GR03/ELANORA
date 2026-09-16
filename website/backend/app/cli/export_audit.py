"""Export this installation's audit trail for a compliance request."""

import argparse
import asyncio
import sys
from datetime import UTC, datetime
from pathlib import Path

from app.db.database import close_database, get_session_maker, init_database
from app.service.audit_export import export_audit_events


def _moment(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-id", type=int, help="Limit to one project")
    parser.add_argument("--since", type=_moment, help="Earliest moment, ISO 8601")
    parser.add_argument("--until", type=_moment, help="Latest moment, ISO 8601")
    parser.add_argument(
        "--format", choices=("json", "csv"), default="json", dest="output_format"
    )
    parser.add_argument(
        "--output", type=Path, help="File to write; standard output by default"
    )
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    init_database()
    try:
        async with get_session_maker()() as db:
            if arguments.output:
                with arguments.output.open("w", encoding="utf-8", newline="") as target:
                    exported = await export_audit_events(
                        db,
                        target,
                        project_id=arguments.project_id,
                        since=arguments.since,
                        until=arguments.until,
                        output_format=arguments.output_format,
                    )
                print(f"Exported {exported} audit events to {arguments.output}")
            else:
                await export_audit_events(
                    db,
                    sys.stdout,
                    project_id=arguments.project_id,
                    since=arguments.since,
                    until=arguments.until,
                    output_format=arguments.output_format,
                )
    finally:
        await close_database()


def main() -> None:
    """Run the audit export."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
