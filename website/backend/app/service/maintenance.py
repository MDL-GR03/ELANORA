"""Unattended maintenance an installed ELANORA performs for itself.

An institution installs this product; it does not staff a platform team and
should not have to write cron entries for the things that keep research data
recoverable. The installation therefore takes its own encrypted off-host
backup, verifies the newest one, applies each project's retention policy, and
watches the disk its projects live on.

What runs next is decided from the runs already recorded in PostgreSQL, so a
restart never repeats a backup, a missed window is caught up at the next
wake-up, and an administrator can see the real state instead of being told
that backups are somebody else's responsibility.
"""

import os
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.settings import get_settings
from app.model.maintenance_run import MaintenanceRun
from app.service.offsite_backup import (
    BackupError,
    create_offsite_backup,
    dump_with_pg_dump,
    prune_backups,
    verify_latest_backup,
)
from app.service.retention_purge import purge_expired_projects
from app.storage.assets import get_backup_storage

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger()

BACKUP_PASSPHRASE_ENV = "ELANORA_BACKUP_PASSPHRASE"  # noqa: S105 - variable name
CAPACITY_ALARM_PERCENT = 90.0
# A job that failed is worth retrying before its next window, in case the cause
# was transient. One that was skipped waits: nothing changes until an
# administrator configures it, and retrying would record a row every poll.
FAILURE_RETRY_INTERVAL = timedelta(hours=1)
# One advisory lock for the whole schedule: two workers never back up at once.
MAINTENANCE_LOCK_KEY = 8_531_207


class MaintenanceJob(StrEnum):
    """The unattended jobs, named as they are recorded."""

    BACKUP = "backup"
    BACKUP_VERIFICATION = "backup_verification"
    RETENTION_PURGE = "retention_purge"
    STORAGE_CAPACITY = "storage_capacity"

    @property
    def interval(self) -> timedelta:
        """How long a successful run stays fresh."""
        return {
            MaintenanceJob.BACKUP: timedelta(hours=24),
            MaintenanceJob.BACKUP_VERIFICATION: timedelta(days=7),
            MaintenanceJob.RETENTION_PURGE: timedelta(hours=24),
            MaintenanceJob.STORAGE_CAPACITY: timedelta(hours=1),
        }[self]


@dataclass(frozen=True, slots=True)
class LastRun:
    """The most recent attempt at a job, whatever came of it."""

    started_at: datetime
    outcome: str

    def next_due(self, interval: timedelta) -> datetime:
        if self.outcome == "failed":
            return self.started_at + min(FAILURE_RETRY_INTERVAL, interval)
        return self.started_at + interval


@dataclass(frozen=True, slots=True)
class JobResult:
    """What one job did, recorded without any research content."""

    outcome: str
    detail: dict[str, Any]


def due_jobs(
    last_runs: dict[MaintenanceJob, LastRun], *, now: datetime | None = None
) -> list[MaintenanceJob]:
    """Jobs that never ran, or whose last attempt is no longer fresh."""
    moment = now or datetime.now(UTC)
    return [
        job
        for job in MaintenanceJob
        if job not in last_runs or last_runs[job].next_due(job.interval) <= moment
    ]


def capacity_outcome(used_percent: float) -> str:
    """A disk this full stops the installation accepting research."""
    return "failed" if used_percent >= CAPACITY_ALARM_PERCENT else "succeeded"


async def latest_run_records(db: AsyncSession) -> dict[MaintenanceJob, MaintenanceRun]:
    """Each job's most recent attempt, with everything it recorded."""
    newest = (
        select(MaintenanceRun.job, func.max(MaintenanceRun.started_at).label("started"))
        .group_by(MaintenanceRun.job)
        .subquery()
    )
    rows = (
        await db.scalars(
            select(MaintenanceRun).join(
                newest,
                (MaintenanceRun.job == newest.c.job)
                & (MaintenanceRun.started_at == newest.c.started),
            )
        )
    ).all()
    recorded = {}
    for row in rows:
        try:
            recorded[MaintenanceJob(row.job)] = row
        except ValueError:  # pragma: no cover - a job removed in a later version
            continue
    return recorded


async def latest_runs(db: AsyncSession) -> dict[MaintenanceJob, LastRun]:
    """Each job's most recent attempt, reduced to what scheduling needs."""
    return {
        job: LastRun(run.started_at, run.outcome)
        for job, run in (await latest_run_records(db)).items()
    }


async def record_run(
    db: AsyncSession,
    job: MaintenanceJob,
    result: JobResult,
    *,
    started_at: datetime,
) -> MaintenanceRun:
    """Keep what a job did, so the next one is scheduled from fact."""
    run = MaintenanceRun(
        job=job.value,
        outcome=result.outcome,
        started_at=started_at,
        finished_at=datetime.now(UTC),
        detail=result.detail,
    )
    db.add(run)
    await db.flush()
    return run


def _backup_passphrase() -> str | None:
    return os.environ.get(BACKUP_PASSPHRASE_ENV) or None


def run_backup() -> JobResult:
    """Take tonight's encrypted backup and drop copies beyond the retained set."""
    passphrase = _backup_passphrase()
    if passphrase is None:
        # Surfaced to the administrator rather than failing quietly: an
        # installation without this configured has no recoverable backup.
        return JobResult("skipped", {"reason": "backup_passphrase_not_configured"})
    settings = get_settings()
    storage = get_backup_storage()
    report = create_offsite_backup(
        storage=storage,
        projects=Path(settings.elan_projects_base_path),
        assets=Path(settings.instance_assets_base_path),
        passphrase=passphrase,
        dump_database=dump_with_pg_dump(
            settings.resolved_database_url.replace("+asyncpg", "")
        ),
    )
    removed = prune_backups(storage, keep=settings.backup_retain_copies)
    return JobResult(
        "succeeded",
        {"key": report.key, "size_bytes": report.size_bytes, "pruned": len(removed)},
    )


def run_backup_verification() -> JobResult:
    """Read the newest backup back and check it against its own manifest."""
    passphrase = _backup_passphrase()
    if passphrase is None:
        return JobResult("skipped", {"reason": "backup_passphrase_not_configured"})
    report = verify_latest_backup(get_backup_storage(), passphrase)
    return JobResult("succeeded", {"key": report.key, "files": len(report.files)})


def run_storage_capacity() -> JobResult:
    """Watch the volume research data is written to."""
    root = Path(get_settings().elan_projects_base_path).resolve()
    probe = root if root.exists() else root.parent
    usage = shutil.disk_usage(probe)
    used_percent = round(usage.used / usage.total * 100, 1) if usage.total else 0.0
    return JobResult(
        capacity_outcome(used_percent),
        {
            "used_percent": used_percent,
            "free_bytes": usage.free,
            "total_bytes": usage.total,
            "alarm_percent": CAPACITY_ALARM_PERCENT,
        },
    )


async def run_retention_purge(db: AsyncSession) -> JobResult:
    """Destroy the content of projects whose retention period has ended."""
    report = await purge_expired_projects(db)
    return JobResult("succeeded", {"projects_purged": len(report.purged)})


async def run_job(db: AsyncSession, job: MaintenanceJob) -> JobResult:
    """Run one job, turning any failure into a recorded outcome."""
    blocking: Callable[[], JobResult] | None = {
        MaintenanceJob.BACKUP: run_backup,
        MaintenanceJob.BACKUP_VERIFICATION: run_backup_verification,
        MaintenanceJob.STORAGE_CAPACITY: run_storage_capacity,
    }.get(job)
    try:
        if blocking is not None:
            return blocking()
        return await run_retention_purge(db)
    except BackupError as error:
        logger.error("Scheduled %s failed: %s", job.value, error)
        return JobResult("failed", {"error": str(error)})
    except Exception as error:
        logger.error(
            "Scheduled %s failed; error_type=%s", job.value, safe_exception_type(error)
        )
        return JobResult("failed", {"error_type": safe_exception_type(error)})


async def run_due_maintenance(
    db: AsyncSession, *, now: datetime | None = None
) -> list[MaintenanceRun]:
    """Run whatever is due and record each attempt.

    Held under one advisory lock so a second worker, or an administrator
    running the command by hand, never takes two backups at once.
    """
    locked = bool(
        await db.scalar(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": MAINTENANCE_LOCK_KEY}
        )
    )
    if not locked:
        logger.info("Another process is already running scheduled maintenance")
        return []
    try:
        pending = due_jobs(await latest_runs(db), now=now)
        runs = []
        for job in pending:
            started_at = datetime.now(UTC)
            result = await run_job(db, job)
            runs.append(await record_run(db, job, result, started_at=started_at))
            await db.commit()
            logger.info("Scheduled %s finished: %s", job.value, result.outcome)
        return runs
    finally:
        await db.execute(
            text("SELECT pg_advisory_unlock(:key)"), {"key": MAINTENANCE_LOCK_KEY}
        )
