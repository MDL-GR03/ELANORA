"""Deciding which unattended maintenance is due, and what counts as an alarm.

ELANORA is installed by an institution, not run by a platform team. It has to
take its own backups, verify them, purge what its retention policy says to
purge, and notice when its disk is filling up, without anyone writing a cron
entry. The schedule is decided from what the database says already ran, so a
restart never repeats a backup and a missed window is caught up at the next
wake-up.
"""

from datetime import UTC, datetime, timedelta

import pytest

from app.service.maintenance import (
    CAPACITY_ALARM_PERCENT,
    LastRun,
    MaintenanceJob,
    capacity_outcome,
    due_jobs,
)

NOW = datetime(2026, 9, 16, 3, 0, tzinfo=UTC)


def _ran(hours_ago: float, outcome: str = "succeeded") -> LastRun:
    return LastRun(NOW - timedelta(hours=hours_ago), outcome)


def test_a_job_that_never_ran_is_due_immediately() -> None:
    assert MaintenanceJob.BACKUP in due_jobs({}, now=NOW)


def test_a_job_is_not_repeated_inside_its_interval() -> None:
    """A restart must not take a second backup minutes after the first."""
    recent = {MaintenanceJob.BACKUP: _ran(1)}

    assert MaintenanceJob.BACKUP not in due_jobs(recent, now=NOW)


def test_a_missed_window_is_caught_up_rather_than_skipped() -> None:
    """An installation switched off overnight still gets yesterday's backup."""
    stale = {MaintenanceJob.BACKUP: _ran(72)}

    assert MaintenanceJob.BACKUP in due_jobs(stale, now=NOW)


def test_each_job_keeps_its_own_schedule() -> None:
    last_run = {
        MaintenanceJob.BACKUP: _ran(1),
        MaintenanceJob.BACKUP_VERIFICATION: _ran(1),
        MaintenanceJob.RETENTION_PURGE: _ran(1),
        MaintenanceJob.STORAGE_CAPACITY: _ran(2),
    }

    # Verification is weekly, capacity hourly: only the hourly one is due again.
    assert due_jobs(last_run, now=NOW) == [MaintenanceJob.STORAGE_CAPACITY]


def test_backups_are_verified_less_often_than_they_are_taken() -> None:
    assert MaintenanceJob.BACKUP_VERIFICATION.interval > MaintenanceJob.BACKUP.interval


@pytest.mark.parametrize(
    ("used_percent", "expected"),
    [
        (10.0, "succeeded"),
        (89.9, "succeeded"),
        (CAPACITY_ALARM_PERCENT, "failed"),
        (99.0, "failed"),
    ],
)
def test_a_filling_disk_is_reported_as_an_alarm(
    used_percent: float, expected: str
) -> None:
    """Running out of room is what stops an installation accepting research."""
    assert capacity_outcome(used_percent) == expected


def test_a_failed_job_is_retried_before_its_next_window() -> None:
    """A backup that failed on a transient error should not wait a whole day."""
    failed_an_hour_ago = {MaintenanceJob.BACKUP: _ran(1, "failed")}

    assert MaintenanceJob.BACKUP in due_jobs(failed_an_hour_ago, now=NOW)


def test_a_skipped_job_waits_like_a_successful_one() -> None:
    """Nothing changes until an administrator configures it.

    Retrying every poll would write a row each time and drown the real history.
    """
    skipped_recently = {
        MaintenanceJob.BACKUP: _ran(1, "skipped"),
        MaintenanceJob.BACKUP_VERIFICATION: _ran(1, "skipped"),
        MaintenanceJob.RETENTION_PURGE: _ran(1),
        MaintenanceJob.STORAGE_CAPACITY: _ran(0.1),
    }

    assert due_jobs(skipped_recently, now=NOW) == []
