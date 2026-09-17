from pathlib import Path
from tempfile import SpooledTemporaryFile
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import UploadFile

from app.service.elan import ElanFileOutcome
from app.service.git import GitService
from app.service.git_command_runner import GitCommandRunner


def eaf_upload(filename: str = "session.eaf") -> UploadFile:
    """Build the same in-memory upload shape produced by Starlette."""
    file = SpooledTemporaryFile()  # noqa: SIM115 - UploadFile owns this handle.
    file.write(b"<eaf/>")
    file.seek(0)
    return UploadFile(filename=filename, file=file)


def test_init_repo_sets_an_application_owned_commit_identity(tmp_path: Path) -> None:
    """A container must not need a global Git identity to create projects."""
    with patch("app.service.git_backup.update_backup"):
        runner = GitCommandRunner(tmp_path, maintain_backup=False)
        runner.init_repo()

    assert runner.run(["config", "user.name"], check=True).stdout.strip() == "ELANORA"
    assert (
        runner.run(["config", "user.email"], check=True).stdout.strip()
        == "system@elanora.local"
    )


@pytest.mark.asyncio
async def test_project_creation_succeeds_without_optional_central_hooks(
    tmp_path: Path,
) -> None:
    """A default installation can create an empty, valid project repository."""
    service = GitService(base_path=str(tmp_path))
    db = AsyncMock()
    project = type("CreatedProject", (), {"project_id": 42})()
    append_revision = AsyncMock()

    with (
        patch(
            "app.service.project_lifecycle.project_exists_by_name",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.service.project_lifecycle.create_project_db",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.service.project_lifecycle.append_project_revision",
            new=append_revision,
        ),
        patch("app.service.project_lifecycle.update_backup"),
    ):
        result = await service.create_project(
            project_name="research-corpus",
            description="A test corpus",
            db=db,
            user_id=1,
            instance_id=1,
        )

    project_path = tmp_path / "research-corpus"
    assert result["status"] == "created"
    assert project_path.is_dir()
    assert (project_path / "elan_files").is_dir()
    assert GitCommandRunner(project_path).get_commit_hash()
    append_revision.assert_awaited_once()
    assert append_revision.await_args.kwargs["project_id"] == 42
    assert append_revision.await_args.kwargs["source_type"] == "migration"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_project_creation_removes_partial_repository(
    tmp_path: Path,
) -> None:
    """A database failure must not leave a project that blocks a retry."""
    service = GitService(base_path=str(tmp_path))
    db = AsyncMock()

    with (
        patch(
            "app.service.project_lifecycle.project_exists_by_name",
            new=AsyncMock(return_value=False),
        ),
        patch("app.service.project_lifecycle.remove_project_backup") as remove_backup,
        patch("app.service.project_lifecycle.copy_githooks"),
        patch("app.service.git_backup.update_backup"),
        patch(
            "app.service.project_lifecycle.create_project_db",
            new=AsyncMock(side_effect=RuntimeError("database unavailable")),
        ),
        pytest.raises(RuntimeError, match="Project creation failed"),
    ):
        await service.create_project(
            project_name="test-project",
            description="",
            db=db,
            user_id=1,
            instance_id=1,
        )

    db.rollback.assert_awaited_once()
    assert not (tmp_path / "test-project").exists()
    remove_backup.assert_called_once_with("test-project")


@pytest.mark.asyncio
async def test_folder_import_publishes_only_after_eaf_projection_succeeds(
    tmp_path: Path,
) -> None:
    service = GitService(base_path=str(tmp_path))
    db = AsyncMock()
    project = type("CreatedProject", (), {"project_id": 42})()
    append_revision = AsyncMock()
    elan_service = MagicMock()
    elan_service.process_single_file = AsyncMock(
        return_value=ElanFileOutcome("processed", "session.eaf", 1)
    )
    upload = eaf_upload()

    with (
        patch(
            "app.service.project_lifecycle.project_exists_by_name",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.service.project_lifecycle.create_project_db",
            new=AsyncMock(return_value=project),
        ),
        patch(
            "app.service.project_lifecycle.append_project_revision",
            new=append_revision,
        ),
        patch("app.service.project_lifecycle.ElanService", return_value=elan_service),
        patch("app.service.project_lifecycle.update_backup"),
    ):
        result = await service.init_project_from_folder_upload(
            "imported-corpus", "Imported", [upload], db, 7, 3
        )

    assert result["status"] == "initialized"
    assert result["processed_files"] == ["session.eaf"]
    assert (tmp_path / "imported-corpus" / "elan_files" / "session.eaf").exists()
    append_revision.assert_awaited_once()
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_failed_folder_import_leaves_no_project_repository(
    tmp_path: Path,
) -> None:
    service = GitService(base_path=str(tmp_path))
    db = AsyncMock()
    project = type("CreatedProject", (), {"project_id": 42})()
    elan_service = MagicMock()
    elan_service.process_single_file = AsyncMock(
        side_effect=RuntimeError("invalid projection")
    )
    upload = eaf_upload()

    with (
        patch(
            "app.service.project_lifecycle.project_exists_by_name",
            new=AsyncMock(return_value=False),
        ),
        patch(
            "app.service.project_lifecycle.create_project_db",
            new=AsyncMock(return_value=project),
        ),
        patch("app.service.project_lifecycle.ElanService", return_value=elan_service),
        patch("app.service.project_lifecycle.remove_project_backup"),
        pytest.raises(RuntimeError, match="invalid projection"),
    ):
        await service.init_project_from_folder_upload(
            "failed-import", "Imported", [upload], db, 7, 3
        )

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
    assert not (tmp_path / "failed-import").exists()
    assert not list(tmp_path.glob(".failed-import.staging-*"))
