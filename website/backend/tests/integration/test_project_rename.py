"""Renaming a project moves its folder, recovery backup and record together.

These stores cannot share a transaction, so a failure part-way must put every
store back rather than leave a folder under one name and a record under another.
"""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.instance import Instance
from app.model.project import Project
from app.service.git import GitService
from app.service.git_operations import GitCommandRunner


@pytest.fixture
def roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    projects = tmp_path / "projects"
    backups = tmp_path / "backups"
    projects.mkdir()
    backups.mkdir()
    monkeypatch.setattr("app.utils.project_backup.ELAN_BACKUPS_BASE_PATH", str(backups))
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_a: None)
    return projects, backups


async def _institution(session: AsyncSession) -> Instance:
    institution = Instance(
        instance_name="Rename Institute",
        institution_name="Rename Institute",
        contact_email="admin@rename-project.example",
        domain="rename-project.example",
        timezone="UTC",
    )
    session.add(institution)
    await session.flush()
    return institution


async def _project(
    session: AsyncSession,
    institution: Instance,
    projects: Path,
    backups: Path,
    name: str,
    *,
    with_backup: bool = True,
) -> Project:
    folder = projects / name
    (folder / "elan_files").mkdir(parents=True)
    (folder / "elan_files" / "session.eaf").write_text(f"{name} annotations")
    runner = GitCommandRunner(folder, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA rename test"], check=True)
    runner.run(["config", "user.email", "rename@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Baseline"], check=True)
    if with_backup:
        (backups / name).mkdir()
        (backups / name / "RECOVERY").write_text(f"{name} recovery cache")
    project = Project(project_name=name, project_path=str(folder), instance=institution)
    session.add(project)
    await session.commit()
    return project


async def _record(session: AsyncSession, project_id: int) -> tuple[str, str]:
    session.expire_all()
    row = (
        await session.execute(
            select(Project.project_name, Project.project_path).where(
                Project.project_id == project_id
            )
        )
    ).one()
    return row.project_name, row.project_path


@pytest.mark.asyncio
async def test_a_rename_moves_folder_backup_and_record_together(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    projects, backups = roots
    institution = await _institution(session)
    project = await _project(session, institution, projects, backups, "beta")
    project_id = project.project_id

    await GitService(base_path=str(projects)).edit_project(
        "beta", "gamma", "Renamed corpus", session
    )

    assert not (projects / "beta").exists()
    assert (projects / "gamma" / "elan_files" / "session.eaf").exists()
    assert (backups / "gamma" / "RECOVERY").read_text() == "beta recovery cache"
    name, path = await _record(session, project_id)
    assert name == "gamma"
    assert Path(path) == projects / "gamma"


@pytest.mark.asyncio
async def test_a_project_without_a_recovery_backup_can_still_be_renamed(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    """A recovery cache that does not exist yet is nothing to move, not an error."""
    projects, backups = roots
    institution = await _institution(session)
    project = await _project(
        session, institution, projects, backups, "beta", with_backup=False
    )
    project_id = project.project_id

    await GitService(base_path=str(projects)).edit_project(
        "beta", "gamma", None, session
    )

    assert (projects / "gamma").exists()
    assert not (projects / "beta").exists()
    assert (await _record(session, project_id))[0] == "gamma"


@pytest.mark.asyncio
async def test_a_deleted_projects_name_is_refused_without_moving_anything(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    """A deleted project is retained and restorable by name, so its name is taken.

    Reusing it would put a live project's files where restoring the deleted
    project writes, and destroy that project's recovery cache.
    """
    projects, backups = roots
    institution = await _institution(session)
    await _project(session, institution, projects, backups, "alpha")
    beta = await _project(session, institution, projects, backups, "beta")
    beta_id = beta.project_id
    service = GitService(base_path=str(projects))
    await service.delete_project("alpha", session)

    with pytest.raises((ValueError, FileExistsError)):
        await service.edit_project("beta", "alpha", None, session)

    await session.rollback()
    assert (projects / "beta" / "elan_files" / "session.eaf").exists()
    assert not (projects / "alpha").exists()
    assert (backups / "alpha" / "RECOVERY").read_text() == "alpha recovery cache"
    assert (backups / "beta" / "RECOVERY").read_text() == "beta recovery cache"
    assert (await _record(session, beta_id))[0] == "beta"


@pytest.mark.asyncio
async def test_a_late_failure_puts_folder_and_backup_back(
    session: AsyncSession, roots: tuple[Path, Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    projects, backups = roots
    institution = await _institution(session)
    project = await _project(session, institution, projects, backups, "beta")
    project_id = project.project_id

    def refuse(*_args: object, **_kwargs: object) -> None:
        raise OSError("hooks directory is read-only")

    monkeypatch.setattr("app.service.project_lifecycle.update_project_githooks", refuse)

    with pytest.raises(OSError):
        await GitService(base_path=str(projects)).edit_project(
            "beta", "gamma", None, session
        )

    await session.rollback()
    assert (projects / "beta" / "elan_files" / "session.eaf").exists()
    assert not (projects / "gamma").exists()
    assert (backups / "beta" / "RECOVERY").exists()
    assert not (backups / "gamma").exists()
    assert (await _record(session, project_id))[0] == "beta"


@pytest.mark.asyncio
async def test_changing_only_the_description_moves_nothing(
    session: AsyncSession, roots: tuple[Path, Path]
) -> None:
    projects, backups = roots
    institution = await _institution(session)
    project = await _project(session, institution, projects, backups, "beta")
    project_id = project.project_id

    result = await GitService(base_path=str(projects)).edit_project(
        "beta", "beta", "A clearer description", session
    )

    assert result["new_project_description"] == "A clearer description"
    assert (projects / "beta").exists()
    assert (backups / "beta" / "RECOVERY").exists()
    session.expire_all()
    refreshed = await session.get(Project, project_id)
    assert refreshed is not None and refreshed.description == "A clearer description"
