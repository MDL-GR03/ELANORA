"""Publish queued contribution change sets once or continuously."""

import argparse
import asyncio

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.db.database import close_database, get_session_maker, init_database
from app.dependency.project_lock import acquire_project_write_lock
from app.model.contribution_change_set import ContributionChangeSet
from app.service.contribution_change_set import ContributionChangeSetCoordinator
from app.service.git import GitService

logger = get_logger()


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="Drain once and exit")
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--poll-seconds", type=float, default=5.0)
    return parser.parse_args()


async def dispatch_batch(
    coordinator: ContributionChangeSetCoordinator, limit: int
) -> int:
    """Execute up to ``limit`` queued operations and return the completed count."""
    completed = 0
    async with get_session_maker()() as db:
        await coordinator.requeue_interrupted(db)
    for _ in range(limit):
        async with get_session_maker()() as db:
            change_set_id = await coordinator.next_retryable_id(db)
            if change_set_id is None:
                break
            change_set = await db.get(ContributionChangeSet, change_set_id)
            if change_set is None:
                continue
            project_id = change_set.project_id
        try:
            async with (
                acquire_project_write_lock(
                    project_id, coordinator.git_service.base_path
                ),
                get_session_maker()() as db,
            ):
                result = await coordinator.execute(db, change_set_id)
                if result.get("change_set_state") == "completed":
                    completed += 1
        except Exception as error:
            logger.error(
                "Contribution change-set publication failed; error_type=%s",
                safe_exception_type(error),
            )
            break
    return completed


async def _main() -> None:
    arguments = _arguments()
    if arguments.batch_size < 1 or arguments.poll_seconds <= 0:
        raise ValueError("batch size and poll interval must be positive")

    init_database()
    coordinator = ContributionChangeSetCoordinator(GitService())
    try:
        while True:
            await dispatch_batch(coordinator, arguments.batch_size)
            if arguments.once:
                break
            await asyncio.sleep(arguments.poll_seconds)
    finally:
        await close_database()


def main() -> None:
    """Run the contribution change-set worker."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
