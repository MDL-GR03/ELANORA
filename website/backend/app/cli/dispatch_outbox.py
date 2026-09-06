"""Publish queued ELANORA outbox events once or continuously."""

import argparse
import asyncio

from app.db.database import close_database, get_session_maker, init_database
from app.service.outbox import OutboxDispatcher


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Drain once and exit")
    parser.add_argument("--batch-size", type=int, default=100)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    return parser.parse_args()


async def _main() -> None:
    arguments = _arguments()
    if arguments.batch_size < 1 or arguments.poll_seconds <= 0:
        raise ValueError("batch size and poll interval must be positive")

    init_database()
    dispatcher = OutboxDispatcher()
    try:
        while True:
            async with get_session_maker()() as db:
                await dispatcher.dispatch_pending(db, limit=arguments.batch_size)
            if arguments.once:
                break
            await asyncio.sleep(arguments.poll_seconds)
    finally:
        await close_database()


def main() -> None:
    """Run the outbox dispatcher process."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
