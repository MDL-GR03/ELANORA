"""Queue development-only verification and reset emails for Mailpit testing."""

import asyncio

from app.core.settings import get_settings
from app.db.database import close_database, get_session_maker, init_database
from app.service.outbox import (
    enqueue_account_verification_email,
    enqueue_password_reset_email,
)

VERIFICATION_RECIPIENT = "verification-smoke@dev.elanora.example.org"
RESET_RECIPIENT = "reset-smoke@dev.elanora.example.org"
VERIFICATION_CODE = "VERIFY-OUTBOX-123"
RESET_CODE = "RESET-OUTBOX-456"


async def _main() -> None:
    settings = get_settings()
    if settings.environment not in {"dev", "dev.docker", "test"}:
        raise RuntimeError(
            "test email command is disabled outside development and test"
        )

    init_database()
    try:
        async with get_session_maker()() as db:
            await enqueue_account_verification_email(
                db,
                user_id=0,
                email=VERIFICATION_RECIPIENT,
                username="Verification Smoke Test",
                code=VERIFICATION_CODE,
                language="en",
            )
            await enqueue_password_reset_email(
                db,
                user_id=0,
                email=RESET_RECIPIENT,
                username="Password Reset Smoke Test",
                code=RESET_CODE,
                language="en",
            )
            await db.commit()
        print("Queued encrypted verification and password-reset test emails.")
    finally:
        await close_database()


def main() -> None:
    """Queue both account-email smoke-test events."""
    asyncio.run(_main())


if __name__ == "__main__":
    main()
