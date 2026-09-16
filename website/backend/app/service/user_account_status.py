"""Suspending and restoring accounts, with the guards that protect the institution."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.model.audit_event import AuditEvent
from app.model.enums import UserRole
from app.model.user import User
from app.service.refresh_session import revoke_all_refresh_sessions
from app.service.user_errors import (
    AccountNotFoundError,
    AdministratorNoLongerActiveError,
    LastAdministratorError,
    RedundantAccountStatusError,
    SelfAccountStatusError,
)

logger = get_logger()


async def set_account_active(
    db: AsyncSession,
    *,
    actor: User,
    target_user_id: int,
    is_active: bool,
    reason: str,
) -> User:
    """Suspend or restore an institution account with safety invariants."""
    # Lock the institution's active administrators before anything else, in
    # a fixed order. Every status change takes these locks in the same
    # sequence, so two administrators acting on each other at once queue
    # behind one another instead of deadlocking, and each sees the other's
    # committed decision.
    active_admin_ids = set(
        (
            await db.execute(
                select(User.user_id)
                .where(
                    User.instance_id == actor.instance_id,
                    User.role == UserRole.ADMIN,
                    User.is_active.is_(True),
                )
                .order_by(User.user_id)
                .with_for_update()
            )
        ).scalars()
    )
    # The request was authorized when it began. If this administrator was
    # suspended while it was in flight, it must not complete.
    if actor.user_id not in active_admin_ids:
        raise AdministratorNoLongerActiveError(
            "The acting administrator is no longer active"
        )

    target = await db.scalar(
        select(User)
        .where(
            User.user_id == target_user_id,
            User.instance_id == actor.instance_id,
        )
        .with_for_update()
    )
    if target is None:
        raise AccountNotFoundError("Account not found")
    if target.user_id == actor.user_id:
        raise SelfAccountStatusError(
            "Administrators cannot change their own account status"
        )
    if target.is_active == is_active:
        state = "active" if is_active else "suspended"
        raise RedundantAccountStatusError(f"Account is already {state}")

    # Backstop. An active actor who cannot target themselves already implies
    # a second active administrator survives, but the invariant is too
    # important to rest on that reasoning if either rule above changes.
    remaining = active_admin_ids - {target.user_id}
    if not is_active and target.role == UserRole.ADMIN and not remaining:
        raise LastAdministratorError(
            "The institution must retain an active administrator"
        )

    target.is_active = is_active
    target.updated_at = datetime.now(UTC)
    revoked_sessions = 0
    if not is_active:
        revoked_sessions = await revoke_all_refresh_sessions(db, target.user_id)
    db.add(
        AuditEvent(
            actor_user_id=actor.user_id,
            action="account.reactivated" if is_active else "account.suspended",
            resource_type="user",
            resource_id=str(target.user_id),
            details={
                "reason": reason.strip(),
                "revoked_sessions": revoked_sessions,
            },
        )
    )
    await db.commit()
    await db.refresh(target)
    return target
