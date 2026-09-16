"""Renaming ELAN files must keep database, filesystem and Git in agreement."""

import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import RenameConflictError
from app.crud.elan_file import get_elan_file_name_by_id
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.service.file_rename import FileRenameService
from app.service.git_operations import GitCommandRunner

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
PROJECT_NAME = "rename-corpus"


@pytest.fixture(autouse=True)
def isolate_backups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_a: None)


async def _project(
    session: AsyncSession, tmp_path: Path, filenames: list[str]
) -> tuple[Project, Path, dict[str, int]]:
    institution = Instance(
        instance_name="Rename Institute",
        institution_name="Rename Institute",
        contact_email="admin@rename.example",
        domain="rename.example",
        timezone="UTC",
    )
    project = Project(
        project_name=PROJECT_NAME, project_path=PROJECT_NAME, instance=institution
    )
    session.add_all([institution, project])
    await session.flush()

    project_path = tmp_path / PROJECT_NAME
    (project_path / "elan_files").mkdir(parents=True)
    baseline = EAF_FIXTURE.read_bytes()

    elan_ids: dict[str, int] = {}
    for filename in filenames:
        (project_path / "elan_files" / filename).write_bytes(baseline)
        content = FileContent(
            filename=filename,
            file_size=len(baseline),
            content_hash=hashlib.sha256(filename.encode()).hexdigest(),
        )
        elan_file = ElanFile(
            file_content=content,
            project=project,
            filename=filename,
            file_path=f"{PROJECT_NAME}/elan_files/{filename}",
            last_modified=datetime.now(),
        )
        session.add_all([content, elan_file])
        await session.flush()
        elan_ids[filename] = elan_file.elan_id

    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA rename test"], check=True)
    runner.run(["config", "user.email", "rename-test@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Baseline"], check=True)
    await session.commit()
    return project, project_path, elan_ids


def _service(tmp_path: Path) -> FileRenameService:
    return FileRenameService(tmp_path)


@pytest.mark.asyncio
async def test_a_single_rename_updates_database_filesystem_and_git(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, ids = await _project(session, tmp_path, ["video-11.eaf"])

    result = await _service(tmp_path).rename_one(
        session, PROJECT_NAME, ids["video-11.eaf"], "session-01.eaf"
    )

    assert result.success is True
    assert result.committed is True
    # The response must carry the real commit, not a null placeholder.
    assert (
        result.commit_hash
        == GitCommandRunner(project_path, maintain_backup=False).get_commit_hash()
    )
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "session-01.eaf"
    )
    assert (project_path / "elan_files" / "session-01.eaf").exists()
    assert not (project_path / "elan_files" / "video-11.eaf").exists()
    log = GitCommandRunner(project_path, maintain_backup=False).run(
        ["log", "-1", "--pretty=%s"], check=True
    )
    assert "video-11.eaf -> session-01.eaf" in log.stdout


@pytest.mark.asyncio
async def test_renaming_onto_an_existing_file_is_refused_with_its_identity(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, ids = await _project(
        session, tmp_path, ["video-11.eaf", "session-12.eaf"]
    )

    with pytest.raises(RenameConflictError) as refused:
        await _service(tmp_path).rename_one(
            session, PROJECT_NAME, ids["video-11.eaf"], "session-12.eaf"
        )

    assert refused.value.conflict_elan_id == ids["session-12.eaf"]
    assert refused.value.message_key == "rename_file_conflict"
    # Neither store changed.
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "video-11.eaf"
    )
    assert (project_path / "elan_files" / "video-11.eaf").exists()


@pytest.mark.asyncio
async def test_an_unknown_file_or_project_is_reported_as_missing(
    session: AsyncSession, tmp_path: Path
) -> None:
    await _project(session, tmp_path, ["video-11.eaf"])
    service = _service(tmp_path)

    with pytest.raises(FileNotFoundError):
        await service.rename_one(session, PROJECT_NAME, 999_999, "anything.eaf")

    with pytest.raises(FileNotFoundError):
        await service.rename_one(session, "no-such-project", 1, "anything.eaf")


@pytest.mark.asyncio
async def test_a_failed_commit_leaves_no_rename_behind_in_either_store(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The database transaction and the filesystem must roll back together."""
    _, project_path, ids = await _project(session, tmp_path, ["video-11.eaf"])

    def explode(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("git refused the commit")

    monkeypatch.setattr(GitCommandRunner, "commit", explode)

    with pytest.raises(RuntimeError, match="Failed to rename file"):
        await _service(tmp_path).rename_one(
            session, PROJECT_NAME, ids["video-11.eaf"], "session-01.eaf"
        )

    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "video-11.eaf"
    )
    assert (project_path / "elan_files" / "video-11.eaf").exists()
    assert not (project_path / "elan_files" / "session-01.eaf").exists()


@pytest.mark.asyncio
async def test_a_bulk_rename_applies_every_requested_change_in_one_commit(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, ids = await _project(
        session, tmp_path, ["video-11.eaf", "session-12.eaf"]
    )

    result = await _service(tmp_path).rename_many(
        session,
        PROJECT_NAME,
        [
            {"elan_id": ids["video-11.eaf"], "new_filename": "subject-a.eaf"},
            {"elan_id": ids["session-12.eaf"], "new_filename": "subject-b.eaf"},
        ],
    )

    assert result.successful_renames == 2
    assert result.failed_renames == 0
    assert result.committed is True
    assert (
        result.commit_hash
        == GitCommandRunner(project_path, maintain_backup=False).get_commit_hash()
    )
    assert result.message_key == "bulk_rename_success"
    assert (project_path / "elan_files" / "subject-a.eaf").exists()
    assert (project_path / "elan_files" / "subject-b.eaf").exists()
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "subject-a.eaf"
    )


@pytest.mark.asyncio
async def test_a_bulk_conflict_is_reported_without_stopping_the_other_renames(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, ids = await _project(
        session, tmp_path, ["video-11.eaf", "session-12.eaf", "extra-13.eaf"]
    )

    result = await _service(tmp_path).rename_many(
        session,
        PROJECT_NAME,
        [
            {"elan_id": ids["video-11.eaf"], "new_filename": "session-12.eaf"},
            {"elan_id": ids["extra-13.eaf"], "new_filename": "subject-c.eaf"},
        ],
    )

    assert result.successful_renames == 1
    assert result.failed_renames == 1
    assert result.conflicts_count == 1
    assert result.message_key == "bulk_rename_conflicts"
    conflicted = next(r for r in result.results if not r.success)
    assert conflicted.old_filename == "video-11.eaf"
    assert conflicted.conflict_elan_id == ids["session-12.eaf"]
    assert (project_path / "elan_files" / "subject-c.eaf").exists()
    assert (project_path / "elan_files" / "video-11.eaf").exists()


@pytest.mark.asyncio
async def test_a_bulk_rename_that_cannot_be_committed_is_fully_reversed(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A partially written batch must never survive a failed commit."""
    _, project_path, ids = await _project(
        session, tmp_path, ["video-11.eaf", "session-12.eaf"]
    )

    def explode(*_args: object, **_kwargs: object) -> str:
        raise RuntimeError("git refused the commit")

    monkeypatch.setattr(GitCommandRunner, "commit", explode)

    with pytest.raises(RuntimeError, match="Bulk rename failed"):
        await _service(tmp_path).rename_many(
            session,
            PROJECT_NAME,
            [
                {"elan_id": ids["video-11.eaf"], "new_filename": "subject-a.eaf"},
                {"elan_id": ids["session-12.eaf"], "new_filename": "subject-b.eaf"},
            ],
        )

    for original in ("video-11.eaf", "session-12.eaf"):
        assert (project_path / "elan_files" / original).exists()
    for attempted in ("subject-a.eaf", "subject-b.eaf"):
        assert not (project_path / "elan_files" / attempted).exists()
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "video-11.eaf"
    )
    assert await get_elan_file_name_by_id(session, ids["session-12.eaf"]) == (
        "session-12.eaf"
    )


@pytest.mark.asyncio
async def test_a_batch_with_no_usable_entries_commits_nothing(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, ids = await _project(session, tmp_path, ["video-11.eaf"])

    result = await _service(tmp_path).rename_many(
        session,
        PROJECT_NAME,
        [{"elan_id": None, "new_filename": "subject-a.eaf"}],
    )

    assert result.successful_renames == 0
    assert result.committed is False
    assert result.commit_hash is None
    assert result.message_key == "bulk_rename_errors"
    assert (project_path / "elan_files" / "video-11.eaf").exists()
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "video-11.eaf"
    )


@pytest.mark.asyncio
async def test_a_rename_lands_on_the_accepted_branch_not_a_stray_checkout(
    session: AsyncSession, tmp_path: Path
) -> None:
    """The database records accepted filenames, so the rename commit belongs there."""
    _, project_path, ids = await _project(session, tmp_path, ["video-11.eaf"])
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["checkout", "-b", "upload_crashed_midway"], check=True)
    stray_head = runner.get_commit_hash()

    await _service(tmp_path).rename_one(
        session, PROJECT_NAME, ids["video-11.eaf"], "session-01.eaf"
    )

    branch = runner.run(["rev-parse", "upload_crashed_midway"], check=True)
    assert branch.stdout.strip() == stray_head
    accepted = runner.run(
        ["ls-tree", "--name-only", "master", "elan_files/"], check=True
    ).stdout.split()
    assert "elan_files/session-01.eaf" in accepted
    assert await get_elan_file_name_by_id(session, ids["video-11.eaf"]) == (
        "session-01.eaf"
    )
