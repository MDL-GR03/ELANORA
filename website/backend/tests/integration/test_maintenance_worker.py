"""The installation maintaining itself, against a real database.

An institution should not have to schedule backups by hand, and should not be
told that recoverability is somebody else's responsibility. These tests check
that the schedule is driven by what really ran, that a missing backup
passphrase is reported rather than silently doing nothing, and that the
administrator's status page reflects the result.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.maintenance_run import MaintenanceRun
from app.service import maintenance
from app.service.maintenance import (
    MaintenanceJob,
    latest_runs,
    run_due_maintenance,
)


async def _runs(session: AsyncSession) -> list[MaintenanceRun]:
    return list(
        (
            await session.scalars(
                select(MaintenanceRun).order_by(MaintenanceRun.started_at)
            )
        ).all()
    )


@pytest.fixture
def without_backup_passphrase(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(maintenance.BACKUP_PASSPHRASE_ENV, raising=False)


@pytest.mark.asyncio
async def test_a_fresh_installation_runs_everything_that_is_due(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    runs = await run_due_maintenance(session)
    await session.commit()

    assert {run.job for run in runs} == {job.value for job in MaintenanceJob}
    recorded = await _runs(session)
    assert len(recorded) == len(MaintenanceJob)
    assert all(run.finished_at is not None for run in recorded)


@pytest.mark.asyncio
async def test_an_installation_without_a_passphrase_says_so_instead_of_pretending(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    """Silence here would mean discovering there is no backup during a disaster."""
    await run_due_maintenance(session)
    await session.commit()

    backup = next(
        run for run in await _runs(session) if run.job == MaintenanceJob.BACKUP.value
    )
    assert backup.outcome == "skipped"
    assert backup.detail["reason"] == "backup_passphrase_not_configured"


@pytest.mark.asyncio
async def test_restarting_does_not_repeat_work_that_is_still_fresh(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    await run_due_maintenance(session)
    await session.commit()
    first = len(await _runs(session))

    # A restart minutes later: the hourly capacity check is not yet due either.
    await run_due_maintenance(session)
    await session.commit()

    assert len(await _runs(session)) == first


@pytest.mark.asyncio
async def test_a_missed_window_is_caught_up_at_the_next_wake_up(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    await run_due_maintenance(session)
    await session.commit()
    before = len(await _runs(session))

    later = datetime.now(UTC) + timedelta(days=2)
    await run_due_maintenance(session, now=later)
    await session.commit()

    assert len(await _runs(session)) > before


@pytest.mark.asyncio
async def test_what_each_job_last_did_is_readable_for_scheduling(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    """The next run is decided from these, so they must carry the outcome."""
    await run_due_maintenance(session)
    await session.commit()

    recorded = await latest_runs(session)

    assert recorded[MaintenanceJob.BACKUP].outcome == "skipped"
    assert recorded[MaintenanceJob.RETENTION_PURGE].outcome == "succeeded"


@pytest.mark.asyncio
async def test_the_disk_a_project_is_written_to_is_watched(
    session: AsyncSession, without_backup_passphrase: None
) -> None:
    await run_due_maintenance(session)
    await session.commit()

    capacity = next(
        run
        for run in await _runs(session)
        if run.job == MaintenanceJob.STORAGE_CAPACITY.value
    )
    assert capacity.detail["total_bytes"] > 0
    assert 0 <= capacity.detail["used_percent"] <= 100


@pytest.mark.asyncio
async def test_the_administrator_is_told_the_installation_has_no_backup(
    api_client, institution_accounts, session: AsyncSession, without_backup_passphrase
) -> None:
    """Recoverability is this product's own responsibility, and it must say so."""
    from conftest import Browser  # noqa: PLC0415 - test helper

    browser = Browser(api_client)
    await browser.sign_in(institution_accounts.admin_login)

    before = await browser.get("/api/v1/operations/status")
    assert before.status_code == 200, before.text
    assert before.json()["recovery"] == {
        "responsibility": "installation",
        "latest_backup_at": None,
        "latest_verified_backup_at": None,
        "latest_drill_at": None,
        "state": "not_yet_run",
        "jobs": [],
    }

    await run_due_maintenance(session)
    await session.commit()
    after = (await browser.get("/api/v1/operations/status")).json()["recovery"]

    assert after["state"] == "not_configured", "no passphrase means no usable backup"
    assert after["latest_backup_at"] is None
    reported = {job["job"]: job for job in after["jobs"]}
    assert set(reported) == {job.value for job in MaintenanceJob}
    assert reported["backup"]["detail"]["reason"] == "backup_passphrase_not_configured"
    assert reported["storage_capacity"]["detail"]["used_percent"] >= 0
