"""Reconciling a project folder with the database, and refusing unsafe batches."""

import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.elan.validation import EafValidationError
from app.model.elan_file import ElanFile
from app.model.enums import UserRole
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.model.user import User
from app.service.git_command_runner import (
    GitCommandRunner,
    WorkingTreeOffAcceptedBranchError,
)
from app.service.project_filesystem_sync import ProjectFilesystemSyncService

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
PROJECT_NAME = "sync-corpus"


@pytest.fixture(autouse=True)
def isolate_backups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.service.git_backup.update_backup", lambda *_a: None)


async def _project(
    session: AsyncSession, tmp_path: Path, tracked: list[str]
) -> tuple[Project, Path, int]:
    institution = Instance(
        instance_name="Sync Institute",
        institution_name="Sync Institute",
        contact_email="admin@sync.example",
        domain="sync.example",
        timezone="UTC",
    )
    curator = User(
        username="sync-curator",
        email="curator@sync.example",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Ada",
        last_name="Curator",
        affiliation="Sync Institute",
        department="Linguistics",
        activation_code="fixture",
        instance=institution,
        role=UserRole.ADMIN,
    )
    project = Project(
        project_name=PROJECT_NAME, project_path=PROJECT_NAME, instance=institution
    )
    session.add_all([institution, curator, project])
    await session.flush()

    project_path = tmp_path / PROJECT_NAME
    (project_path / "elan_files").mkdir(parents=True)
    baseline = EAF_FIXTURE.read_bytes()
    for filename in tracked:
        (project_path / "elan_files" / filename).write_bytes(baseline)
        content = FileContent(
            filename=filename,
            file_size=len(baseline),
            content_hash=hashlib.sha256(filename.encode()).hexdigest(),
        )
        session.add_all(
            [
                content,
                ElanFile(
                    file_content=content,
                    project=project,
                    filename=filename,
                    file_path=f"{PROJECT_NAME}/elan_files/{filename}",
                    last_modified=datetime.now(),
                ),
            ]
        )

    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA sync test"], check=True)
    runner.run(["config", "user.email", "sync-test@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Baseline"], check=True)
    await session.commit()
    return project, project_path, curator.user_id


async def _stored_filenames(session: AsyncSession, project_id: int) -> set[str]:
    rows = await session.execute(
        select(ElanFile.filename).where(ElanFile.project_id == project_id)
    )
    return set(rows.scalars())


def _service(tmp_path: Path) -> ProjectFilesystemSyncService:
    return ProjectFilesystemSyncService(tmp_path)


def _staged(project_path: Path) -> str:
    return (
        GitCommandRunner(project_path, maintain_backup=False)
        .run(["diff", "--cached", "--name-only"], check=True)
        .stdout.strip()
    )


@pytest.mark.asyncio
async def test_a_clean_project_reports_itself_in_sync(
    session: AsyncSession, tmp_path: Path
) -> None:
    await _project(session, tmp_path, ["video-11.eaf"])

    result = _service(tmp_path).inspect_project(PROJECT_NAME)

    assert result["in_sync"] is True
    assert result["files_status"] == []


@pytest.mark.asyncio
async def test_inspection_reports_a_new_file_without_staging_it(
    session: AsyncSession, tmp_path: Path
) -> None:
    """A preview must never alter what an administrator has edited."""
    _, project_path, _curator_id = await _project(session, tmp_path, ["video-11.eaf"])
    (project_path / "elan_files" / "session-12.eaf").write_bytes(
        EAF_FIXTURE.read_bytes()
    )

    result = _service(tmp_path).inspect_project(PROJECT_NAME)

    assert result["in_sync"] is False
    assert any("session-12.eaf" in f["filename"] for f in result["files_status"])
    assert _staged(project_path) == ""


@pytest.mark.asyncio
async def test_missing_folders_are_reported_rather_than_raising(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, _curator_id = await _project(session, tmp_path, ["video-11.eaf"])
    service = _service(tmp_path)

    assert service.inspect_project("never-created")["status"] == "missing_folder"

    shutil.rmtree(project_path / "elan_files")
    assert service.inspect_project(PROJECT_NAME)["status"] == "missing_elan_files"


@pytest.mark.asyncio
async def test_synchronizing_ingests_a_new_file_into_the_database(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, project_path, curator_id = await _project(
        session, tmp_path, ["video-11.eaf"]
    )
    (project_path / "elan_files" / "session-12.eaf").write_bytes(
        EAF_FIXTURE.read_bytes()
    )

    result = await _service(tmp_path).synchronize(
        PROJECT_NAME, session, curator_id, None
    )

    assert result["in_sync"] is True
    stored = await _stored_filenames(session, project.project_id)
    assert "session-12.eaf" in stored


@pytest.mark.asyncio
async def test_an_unreadable_eaf_stops_the_batch_before_anything_is_staged(
    session: AsyncSession, tmp_path: Path
) -> None:
    """One unsafe file must not drag a whole folder into a half-applied state."""
    project, project_path, curator_id = await _project(
        session, tmp_path, ["video-11.eaf"]
    )
    (project_path / "elan_files" / "good-12.eaf").write_bytes(EAF_FIXTURE.read_bytes())
    (project_path / "elan_files" / "broken-13.eaf").write_bytes(b"<not-really-eaf/>")

    with pytest.raises(EafValidationError):
        await _service(tmp_path).synchronize(PROJECT_NAME, session, curator_id, None)

    await session.rollback()
    assert _staged(project_path) == ""
    stored = await _stored_filenames(session, project.project_id)
    # The valid companion file was not ingested either.
    assert "good-12.eaf" not in stored


@pytest.mark.asyncio
async def test_a_serialized_preview_is_checked_with_the_same_preflight(
    session: AsyncSession, tmp_path: Path
) -> None:
    _, project_path, _curator_id = await _project(session, tmp_path, ["video-11.eaf"])
    (project_path / "elan_files" / "broken-13.eaf").write_bytes(b"<not-really-eaf/>")
    service = _service(tmp_path)

    with pytest.raises(EafValidationError):
        service.validate_changes(
            PROJECT_NAME,
            [
                {
                    "filename": "elan_files/broken-13.eaf",
                    "status": "added",
                    "description": "added",
                }
            ],
        )


@pytest.mark.asyncio
async def test_a_missing_changed_file_is_refused(
    session: AsyncSession, tmp_path: Path
) -> None:
    await _project(session, tmp_path, ["video-11.eaf"])

    with pytest.raises(ValueError, match="missing"):
        _service(tmp_path).validate_changes(
            PROJECT_NAME,
            [
                {
                    "filename": "elan_files/absent.eaf",
                    "status": "modified",
                    "description": "modified",
                }
            ],
        )


@pytest.mark.asyncio
async def test_synchronizing_never_commits_server_edits_onto_a_stray_branch(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Refuse to synchronize edits made while the tree was stranded.

    They cannot be attributed to the accepted branch, so they are refused rather
    than committed to another branch.
    """
    project, project_path, curator_id = await _project(
        session, tmp_path, ["video-11.eaf"]
    )
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["checkout", "-b", "upload_crashed_midway"], check=True)
    stray_head = runner.get_commit_hash()
    (project_path / "elan_files" / "session-12.eaf").write_bytes(
        EAF_FIXTURE.read_bytes()
    )

    with pytest.raises(WorkingTreeOffAcceptedBranchError):
        await _service(tmp_path).synchronize(PROJECT_NAME, session, curator_id, None)

    await session.rollback()
    assert (
        runner.run(["rev-parse", "upload_crashed_midway"], check=True).stdout.strip()
        == stray_head
    )
    assert "session-12.eaf" not in await _stored_filenames(session, project.project_id)


@pytest.mark.asyncio
async def test_keeping_the_repository_version_returns_to_the_accepted_branch(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Leave the accepted state checked out after discarding server edits.

    No other branch may be rewritten in the process.
    """
    _, project_path, _curator_id = await _project(session, tmp_path, ["video-11.eaf"])
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["checkout", "-b", "upload_crashed_midway"], check=True)
    (project_path / "elan_files" / "interrupted.eaf").write_text("half written")
    runner.run(["add", "elan_files"], check=True)
    runner.run(["commit", "-m", "interrupted upload"], check=True)
    stray_head = runner.get_commit_hash()
    (project_path / "elan_files" / "video-11.eaf").write_text("stray server edit")

    _service(tmp_path).discard_local_changes(PROJECT_NAME)

    current = runner.run(["rev-parse", "--abbrev-ref", "HEAD"], check=True)
    assert current.stdout.strip() == "master"
    assert runner.run(["status", "--porcelain"], check=True).stdout.strip() == ""
    assert (
        runner.run(["rev-parse", "upload_crashed_midway"], check=True).stdout.strip()
        == stray_head
    )
    assert not (project_path / "elan_files" / "interrupted.eaf").exists()
