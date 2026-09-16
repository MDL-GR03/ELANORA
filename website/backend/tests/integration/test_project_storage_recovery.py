"""Recovering a project whose storage went missing, as the sync dialog offers.

When a live project's folder, .git or elan_files disappears, administrators
choose between restoring it from the recovery backup and deleting the project.
"""

import shutil
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.enums import UserRole
from app.model.instance import Instance
from app.model.project import Project
from app.model.user import User
from app.service.git import GitService
from app.service.git_command_runner import GitCommandRunner
from app.utils.project_backup import update_backup

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


@pytest.fixture
def roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    projects = tmp_path / "projects"
    backups = tmp_path / "backups"
    projects.mkdir()
    backups.mkdir()
    monkeypatch.setattr("app.utils.project_backup.ELAN_BACKUPS_BASE_PATH", str(backups))
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_a: None)
    return projects, backups


async def _live_project(
    session: AsyncSession, projects: Path, name: str
) -> tuple[Project, User, GitCommandRunner]:
    institution = Instance(
        instance_name=f"{name} Institute",
        institution_name=f"{name} Institute",
        contact_email=f"admin@{name}.example",
        domain=f"{name}.example",
        timezone="UTC",
    )
    curator = User(
        username=f"{name}-curator",
        email=f"curator@{name}.example",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Ada",
        last_name="Curator",
        affiliation="Institute",
        department="Linguistics",
        activation_code="fixture",
        instance=institution,
        role=UserRole.ADMIN,
    )
    folder = projects / name
    (folder / "elan_files").mkdir(parents=True)
    (folder / "elan_files" / "session-01.eaf").write_bytes(EAF_FIXTURE.read_bytes())
    runner = GitCommandRunner(folder, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA recovery test"], check=True)
    runner.run(["config", "user.email", "recovery@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Accepted corpus"], check=True)
    project = Project(project_name=name, project_path=str(folder), instance=institution)
    session.add_all([institution, curator, project])
    await session.commit()
    update_backup(name, projects)
    return project, curator, runner


@pytest.mark.asyncio
@pytest.mark.parametrize("lost", [".", ".git", "elan_files"])
async def test_a_live_project_with_missing_storage_is_restored_from_its_backup(
    session: AsyncSession, roots: tuple[Path, Path], lost: str
) -> None:
    """Restore missing storage, as the sync dialog offers."""
    projects, _ = roots
    project, curator, runner = await _live_project(session, projects, "restorable")
    project_id, curator_id = project.project_id, curator.user_id
    accepted_head = runner.get_commit_hash()
    shutil.rmtree(projects / "restorable" / lost)

    await GitService(base_path=str(projects)).restore_project_from_backup(
        "restorable", session, curator_id
    )

    restored = GitCommandRunner(projects / "restorable", maintain_backup=False)
    assert restored.get_commit_hash() == accepted_head
    assert (projects / "restorable" / "elan_files" / "session-01.eaf").exists()
    session.expire_all()
    record = await session.get(Project, project_id)
    assert record is not None and record.deleted_at is None


@pytest.mark.asyncio
async def test_restore_refuses_to_overwrite_intact_project_storage(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    """Refuse to restore over storage that is still intact.

    A backup can be older than the project, so restoring over intact storage
    would silently discard accepted work newer than that backup.
    """
    projects, _ = roots
    _project, curator, runner = await _live_project(session, projects, "intact")
    curator_id = curator.user_id
    eaf = projects / "intact" / "elan_files" / "session-01.eaf"
    eaf.write_bytes(eaf.read_bytes() + b"\n<!-- accepted after the backup -->")
    runner.run(["commit", "-am", "Newer accepted work"], check=True)
    newer_head = runner.get_commit_hash()
    newer_bytes = eaf.read_bytes()

    with pytest.raises((ValueError, FileExistsError)):
        await GitService(base_path=str(projects)).restore_project_from_backup(
            "intact", session, curator_id
        )

    assert runner.get_commit_hash() == newer_head
    assert eaf.read_bytes() == newer_bytes


@pytest.mark.asyncio
async def test_deleting_a_project_with_missing_storage_discards_it_completely(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    projects, backups = roots
    project, _curator, _ = await _live_project(session, projects, "abandoned")
    project_id = project.project_id
    shutil.rmtree(projects / "abandoned" / ".git")

    await GitService(base_path=str(projects)).decline_project_backup(
        session, "abandoned"
    )

    assert not (projects / "abandoned").exists()
    assert not (backups / "abandoned").exists()
    session.expire_all()
    record = await session.get(Project, project_id)
    assert record is not None and record.deleted_at is not None


@pytest.mark.asyncio
async def test_a_delete_that_cannot_update_the_record_keeps_the_backup(
    session: AsyncSession, roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep the backup if the project cannot be recorded as deleted.

    The backup is the last copy, so it must outlive any failure before the
    deletion is recorded.
    """
    projects, backups = roots
    project, _curator, _ = await _live_project(session, projects, "fragile")
    project_id = project.project_id
    shutil.rmtree(projects / "fragile" / ".git")

    async def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("database unavailable")

    monkeypatch.setattr("app.service.project_recovery.delete_project_db", refuse)

    with pytest.raises(RuntimeError):
        await GitService(base_path=str(projects)).decline_project_backup(
            session, "fragile"
        )

    await session.rollback()
    assert (backups / "fragile" / ".git").exists()
    session.expire_all()
    record = await session.get(Project, project_id)
    assert record is not None and record.deleted_at is None


@pytest.mark.asyncio
async def test_a_failed_restore_puts_partial_storage_back_and_can_be_retried(
    session: AsyncSession, roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    projects, _ = roots
    _project, curator, runner = await _live_project(session, projects, "retry")
    curator_id = curator.user_id
    accepted_head = runner.get_commit_hash()
    shutil.rmtree(projects / "retry" / ".git")
    marker = projects / "retry" / "elan_files" / "unsynced-note.eaf"
    marker.write_text("edited on the server after .git was lost")

    service = GitService(base_path=str(projects))

    async def refuse(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("synchronization failed")

    monkeypatch.setattr(service.filesystem_sync, "synchronize", refuse)
    with pytest.raises(RuntimeError):
        await service.restore_project_from_backup("retry", session, curator_id)

    # Exactly as before the attempt: still missing .git, the server edit kept.
    assert not (projects / "retry" / ".git").exists()
    assert marker.read_text() == "edited on the server after .git was lost"
    assert not list(projects.glob(".retry.pre-restore-*"))

    monkeypatch.undo()
    monkeypatch.setattr(
        "app.utils.project_backup.ELAN_BACKUPS_BASE_PATH", str(roots[1])
    )
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_a: None)
    await GitService(base_path=str(projects)).restore_project_from_backup(
        "retry", session, curator_id
    )
    restored = GitCommandRunner(projects / "retry", maintain_backup=False)
    assert restored.get_commit_hash() == accepted_head
