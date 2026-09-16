"""Run this installation's own scheduled maintenance.

Backups, their verification, retention purges and the disk-capacity check run
here so an institution does not have to add cron entries to the host. What is
due is decided from what already ran, so this process can be restarted, or run
once by hand, without repeating or skipping work.
"""

import argparse
import asyncio
import json

from app.core.centralized_logging import get_logger
from app.db.database import close_database, get_session_maker, init_database
from app.service.maintenance import run_due_maintenance

logger = get_logger()
DEFAULT_POLL_SECONDS = 300.0


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--once", action="store_true", help="Run whatever is due now and exit"
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help="How often to check whether anything is due",
    )
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    if arguments.poll_seconds <= 0:
        raise ValueError("poll interval must be positive")

    init_database()
    try:
        while True:
            async with get_session_maker()() as db:
                runs = await run_due_maintenance(db)
            if arguments.once:
                print(
                    json.dumps(
                        [
                            {
                                "job": run.job,
                                "outcome": run.outcome,
                                "detail": run.detail,
                            }
                            for run in runs
                        ],
                        indent=2,
                        sort_keys=True,
                    )
                )
                break
            await asyncio.sleep(arguments.poll_seconds)
    finally:
        await close_database()


def main() -> None:
    """Run the scheduled maintenance process."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
