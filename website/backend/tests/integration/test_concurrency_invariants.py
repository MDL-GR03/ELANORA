"""Invariants that must survive genuinely concurrent PostgreSQL sessions.

Each test forces contention rather than hoping for it. A blocker session takes
the contended row lock, the competing workers are started, and the test waits
until PostgreSQL reports every worker waiting on that lock. Only then is the
blocker released, so the workers race for the lock at the same moment.
"""

import asyncio
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import Select, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.jwt import create_refresh_token
from app.crud.pending_upload import save_pending_upload
from app.model.contribution_change_set import ContributionChangeSet
from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.project import Project
from app.model.project_revision import ProjectRevision
from app.model.refresh_session import RefreshSession
from app.model.user import User
from app.schema.common.token import TokenData
from app.service.contribution_change_set import ContributionChangeSetCoordinator
from app.service.git import GitService
from app.service.git_operations import GitCommandRunner
from app.service.outbox import (
    OutboxDispatcher,
    enqueue_existing_user_invitation_email,
)
from app.service.project_revision import append_project_revision
from app.service.refresh_session import create_refresh_session
from app.service.user import AdministratorNoLongerActiveError, UserService

Factory = async_sessionmaker[AsyncSession]


async def wait_for_lock_waiters(
    factory: Factory, expected: int, timeout: float = 15.0
) -> None:
    """Poll until ``expected`` backends are blocked waiting on a lock."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    waiting = 0
    while True:
        # A fresh session per poll: pg_stat_activity is snapshotted per transaction.
        async with factory() as observer:
            waiting = int(
                await observer.scalar(
                    text(
                        "SELECT count(*) FROM pg_stat_activity "
                        "WHERE datname = current_database() "
                        "AND wait_event_type = 'Lock'"
                    )
                )
                or 0
            )
        if waiting >= expected:
            return
        if loop.time() > deadline:
            raise AssertionError(
                f"Only {waiting} of {expected} sessions reached the contended lock"
            )
        await asyncio.sleep(0.02)


@asynccontextmanager
async def holding_row_locks(
    factory: Factory, statement: Select[Any]
) -> AsyncIterator[None]:
    """Hold row locks from an independent session until the block exits."""
    async with factory() as blocker:
        await blocker.execute(statement)
        try:
            yield
        finally:
            await blocker.rollback()


async def race[T](
    factory: Factory,
    lock_statement: Select[Any],
    workers: list[Callable[[], Awaitable[T]]],
) -> list[T | BaseException]:
    """Start every worker behind one lock, then release them together."""
    tasks: list[asyncio.Task[T]] = []
    try:
        async with holding_row_locks(factory, lock_statement):
            tasks = [asyncio.create_task(worker()) for worker in workers]
            await wait_for_lock_waiters(factory, len(workers))
    finally:
        results = await asyncio.gather(*tasks, return_exceptions=True)
    return list(results)


def _institution(name: str) -> Instance:
    return Instance(
        instance_name=f"{name} Institute",
        institution_name=f"{name} Institute",
        contact_email=f"admin@{name}.example",
        domain=f"{name}.example",
        timezone="UTC",
    )


def _user(institution: Instance, username: str, role: UserRole) -> User:
    return User(
        username=username,
        email=f"{username}@concurrency.example",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Ada",
        last_name=username.capitalize(),
        affiliation="Institute",
        department="Linguistics",
        activation_code="",
        is_verified_account=True,
        instance=institution,
        role=role,
    )


# --- The accepted revision ledger --------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_revision_appends_receive_distinct_contiguous_ordinals(
    session: AsyncSession, session_factory: Factory
) -> None:
    """Two acceptances landing together must never share a revision number."""
    institution = _institution("ledger")
    project = Project(
        project_name="ledger", project_path="ledger", instance=institution
    )
    session.add_all([institution, project])
    await session.commit()
    project_id = project.project_id

    def append(commit: str) -> Callable[[], Awaitable[int]]:
        async def worker() -> int:
            async with session_factory() as db:
                revision = await append_project_revision(
                    db,
                    project_id=project_id,
                    git_commit=commit,
                    parent_git_commit=None,
                    source_type="migration",
                    actor_user_id=None,
                )
                await db.commit()
                return revision.ordinal

        return worker

    commits = [f"{digit}" * 40 for digit in "abcd"]
    outcomes = await race(
        session_factory,
        select(Project).where(Project.project_id == project_id).with_for_update(),
        [append(commit) for commit in commits],
    )

    assert not [o for o in outcomes if isinstance(o, BaseException)], outcomes
    assert sorted(outcomes) == [1, 2, 3, 4]

    async with session_factory() as db:
        project_now = await db.get(Project, project_id)
        latest = await db.scalar(
            select(ProjectRevision)
            .where(ProjectRevision.project_id == project_id)
            .order_by(ProjectRevision.ordinal.desc())
            .limit(1)
        )
    # The current pointer must land on the newest revision, never rewind.
    assert project_now is not None and latest is not None
    assert project_now.current_revision_id == latest.revision_id


@pytest.mark.asyncio
async def test_concurrent_retries_of_one_commit_record_a_single_revision(
    session: AsyncSession, session_factory: Factory
) -> None:
    """A retried publication racing its original must not duplicate history."""
    institution = _institution("retry")
    project = Project(project_name="retry", project_path="retry", instance=institution)
    session.add_all([institution, project])
    await session.commit()
    project_id = project.project_id

    async def append_same_commit() -> uuid.UUID:
        async with session_factory() as db:
            revision = await append_project_revision(
                db,
                project_id=project_id,
                git_commit="e" * 40,
                parent_git_commit=None,
                source_type="migration",
                actor_user_id=None,
            )
            await db.commit()
            return revision.revision_id

    outcomes = await race(
        session_factory,
        select(Project).where(Project.project_id == project_id).with_for_update(),
        [append_same_commit, append_same_commit, append_same_commit],
    )

    assert not [o for o in outcomes if isinstance(o, BaseException)], outcomes
    assert len(set(outcomes)) == 1
    async with session_factory() as db:
        stored = await db.scalar(
            select(func.count())
            .select_from(ProjectRevision)
            .where(ProjectRevision.project_id == project_id)
        )
    assert stored == 1


# --- Publication workers -----------------------------------------------------


@pytest.mark.asyncio
async def test_competing_workers_never_publish_one_change_set_twice(
    session: AsyncSession,
    session_factory: Factory,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Publishing a contribution twice would rewrite accepted research data."""
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_: None)
    institution = _institution("publish")
    curator = _user(institution, "publish-curator", UserRole.ADMIN)
    project = Project(
        project_name="publish", project_path="publish", instance=institution
    )
    session.add_all([institution, curator, project])
    await session.commit()

    project_path = tmp_path / "publish"
    (project_path / "elan_files").mkdir(parents=True)
    (project_path / "elan_files" / "README").write_text("baseline")
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA concurrency test"], check=True)
    runner.run(["config", "user.email", "concurrency@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Baseline"], check=True)
    head = runner.get_commit_hash()

    upload = await save_pending_upload(
        session,
        project.project_id,
        "contribution-branch",
        {"uploaded_by": curator.username, "modified_files": []},
        submitted_by=curator.user_id,
        base_commit=head,
    )
    change_set = ContributionChangeSet(
        project_id=project.project_id,
        upload_id=upload.upload_id,
        requested_by=curator.user_id,
        branch_name="contribution-branch",
        resolution_strategy="auto",
        expected_commit=head,
        state="queued",
    )
    session.add(change_set)
    await session.commit()
    change_set_id = change_set.change_set_id

    git_service = GitService(base_path=str(tmp_path))
    publications: list[str] = []

    async def slow_publication(*_args: object, **_kwargs: object) -> dict[str, str]:
        publications.append("published")
        await asyncio.sleep(0.2)
        return {"accepted_commit": "f" * 40}

    monkeypatch.setattr(git_service, "complete_pending_upload", slow_publication)
    coordinator = ContributionChangeSetCoordinator(git_service)

    async def execute() -> dict[str, Any]:
        async with session_factory() as db:
            return await coordinator.execute(db, change_set_id)

    outcomes = await race(
        session_factory,
        select(ContributionChangeSet)
        .where(ContributionChangeSet.change_set_id == change_set_id)
        .with_for_update(),
        [execute, execute, execute],
    )

    assert not [o for o in outcomes if isinstance(o, BaseException)], outcomes
    assert publications == ["published"]
    async with session_factory() as db:
        final = await db.get(ContributionChangeSet, change_set_id)
    assert final is not None
    assert final.state == "completed"
    assert final.attempts == 1


# --- Email delivery ----------------------------------------------------------


@dataclass
class SlowSender:
    """Records deliveries and how many overlapped, holding each row lock briefly."""

    delivered: list[int] = field(default_factory=list)
    in_flight: int = 0
    peak_in_flight: int = 0

    async def send_existing_user_invitation_email(
        self, email: str, invitation_id: int, **_kwargs: object
    ) -> bool:
        self.in_flight += 1
        self.peak_in_flight = max(self.peak_in_flight, self.in_flight)
        try:
            await asyncio.sleep(0.1)
            self.delivered.append(invitation_id)
            return True
        finally:
            self.in_flight -= 1

    async def send_email_verification_code(self, **_kwargs: object) -> bool:
        raise AssertionError("not used")

    async def send_password_reset_verification_email(self, **_kwargs: object) -> bool:
        raise AssertionError("not used")


@pytest.mark.asyncio
async def test_competing_dispatchers_never_deliver_an_email_twice(
    session: AsyncSession, session_factory: Factory
) -> None:
    """A verification code or invitation must reach its recipient exactly once."""
    for invitation_id in range(1, 9):
        await enqueue_existing_user_invitation_email(
            session,
            invitation_id=invitation_id,
            email=f"researcher{invitation_id}@external.example",
            sender_name="Ada Admin",
            project_name="Signed corpus",
            custom_message=None,
            language="en",
        )
    await session.commit()

    sender = SlowSender()

    async def drain() -> int:
        async with session_factory() as db:
            return await OutboxDispatcher(sender).dispatch_pending(db, limit=20)

    outcomes = await asyncio.gather(drain(), drain(), drain())

    # Without real overlap this test would prove nothing about SKIP LOCKED.
    assert sender.peak_in_flight >= 2
    assert sorted(sender.delivered) == list(range(1, 9))
    assert sum(outcomes) == 8


# --- Sessions and accounts ---------------------------------------------------


@pytest.mark.asyncio
async def test_a_refresh_token_replayed_concurrently_is_honoured_once(
    session: AsyncSession, session_factory: Factory
) -> None:
    """A stolen refresh token raced against its owner must not fork the session."""
    institution = _institution("replay")
    user = _user(institution, "replay-researcher", UserRole.PUBLIC)
    session.add_all([institution, user])
    await session.flush()
    session_id = uuid.uuid4()
    token = create_refresh_token(
        TokenData(sub=str(user.user_id), session_id=str(session_id))
    )
    await create_refresh_session(session, user.user_id, session_id, token)
    await session.commit()

    async def refresh() -> dict[str, Any]:
        async with session_factory() as db:
            return await UserService.refresh_user_tokens(db, token)

    outcomes = await race(
        session_factory,
        select(RefreshSession)
        .where(RefreshSession.session_id == session_id)
        .with_for_update(),
        [refresh, refresh, refresh],
    )

    assert not [o for o in outcomes if isinstance(o, BaseException)], outcomes
    successes = [o for o in outcomes if isinstance(o, dict) and o["success"]]
    assert len(successes) == 1


@pytest.mark.asyncio
async def test_administrators_suspending_each_other_keep_one_administrator(
    session: AsyncSession, session_factory: Factory
) -> None:
    """Two administrators racing to suspend each other must not lock everyone out."""
    institution = _institution("mutual")
    first = _user(institution, "first-admin", UserRole.ADMIN)
    second = _user(institution, "second-admin", UserRole.ADMIN)
    session.add_all([institution, first, second])
    await session.commit()

    def suspend(actor: User, target: User) -> Callable[[], Awaitable[User]]:
        async def worker() -> User:
            async with session_factory() as db:
                return await UserService.set_account_active(
                    db,
                    actor=actor,
                    target_user_id=target.user_id,
                    is_active=False,
                    reason="Racing suspension",
                )

        return worker

    outcomes = await race(
        session_factory,
        select(User)
        .where(User.user_id.in_([first.user_id, second.user_id]))
        .with_for_update(),
        [suspend(first, second), suspend(second, first)],
    )

    # Previously the loser surfaced a raw DeadlockDetectedError, a 500 to the
    # administrator. Now exactly one suspension lands, and the other is refused
    # because its own actor was the one just suspended.
    assert sum(1 for o in outcomes if isinstance(o, User)) == 1
    refusals = [o for o in outcomes if isinstance(o, BaseException)]
    assert len(refusals) == 1
    assert isinstance(refusals[0], AdministratorNoLongerActiveError), refusals

    async with session_factory() as db:
        active_admins = await db.scalar(
            select(func.count())
            .select_from(User)
            .where(
                User.instance_id == institution.instance_id,
                User.role == UserRole.ADMIN,
                User.is_active.is_(True),
            )
        )
    assert active_admins == 1
