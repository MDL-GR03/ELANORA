from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from app.service.git import GitService
from app.service.git_operations import GitCommandRunner


def test_init_repo_sets_an_application_owned_commit_identity(tmp_path: Path) -> None:
    """A container must not need a global Git identity to create projects."""
    with patch("app.service.git_operations.update_backup"):
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

    with (
        patch(
            "app.service.git.project_exists_by_name", new=AsyncMock(return_value=False)
        ),
        patch("app.service.git.create_project_db", new=AsyncMock()),
        patch("app.service.git.update_backup"),
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
            "app.service.git.project_exists_by_name", new=AsyncMock(return_value=False)
        ),
        patch("app.service.git.remove_project_backup") as remove_backup,
        patch("app.service.git.copy_githooks"),
        patch("app.service.git_operations.update_backup"),
        patch(
            "app.service.git.create_project_db",
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
