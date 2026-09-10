import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.service.git import GitService


def git(repo: Path, *args: str) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def commit_file(repo: Path, content: str, message: str) -> str:
    (repo / "README.md").write_text(content, encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-m", message)
    return git(repo, "rev-parse", "HEAD")


def git_bytes(repo: Path, *args: str) -> bytes:
    return subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
    ).stdout


@pytest.mark.asyncio
async def test_restore_creates_descendant_and_keeps_forward_version(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "test-project"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "ELANORA test")
    git(repo, "config", "user.email", "test@elanora.local")
    latin_eaf = (
        '<?xml version="1.0" encoding="ISO-8859-1"?>\n'
        '<ANNOTATION_DOCUMENT AUTHOR="caf\xe9" '
        'DATE="2026-09-10T00:00:00+00:00" FORMAT="3.0" VERSION="3.0">\n'
        '  <HEADER MEDIA_FILE="" TIME_UNITS="milliseconds"/>\n'
        "  <TIME_ORDER/>\n"
        "</ANNOTATION_DOCUMENT>\n"
    ).encode("latin-1")
    (repo / "elan_files").mkdir()
    (repo / "elan_files" / "latin.eaf").write_bytes(latin_eaf)
    git(repo, "add", "elan_files/latin.eaf")
    first = commit_file(repo, "first\n", "Initial state")
    second = commit_file(repo, "second\n", "Accepted contribution")

    service = GitService(str(tmp_path))
    service.rebuild_project_database = AsyncMock()
    project = SimpleNamespace(project_id=12, project_name="test-project")

    async def project_lookup(*_args: object) -> object:
        return project

    monkeypatch.setattr(
        "app.service.project_history.get_project_by_name", project_lookup
    )
    monkeypatch.setattr(
        "app.service.project_history.get_pending_uploads", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        "app.service.project_history.append_project_revision", AsyncMock()
    )
    monkeypatch.setattr(
        "app.service.project_history.update_backup", lambda *_args: None
    )
    db = AsyncMock()
    db.add = MagicMock()

    restored_first = await service.restore_project_version(
        "test-project",
        first,
        second,
        "The second accepted version was approved by mistake.",
        "RESTORE test-project",
        db,
        7,
    )
    third = restored_first["restored_commit"]
    assert git(repo, "show", "HEAD:README.md") == "first"
    assert git_bytes(repo, "show", "HEAD:elan_files/latin.eaf") == latin_eaf
    assert git(repo, "merge-base", "--is-ancestor", second, third) == ""
    assert git(repo, "rev-parse", f"{third}^{{tree}}") == git(
        repo, "rev-parse", f"{first}^{{tree}}"
    )

    restored_second = await service.restore_project_version(
        "test-project",
        second,
        third,
        "Reapply the later accepted state after checking the earlier version.",
        "RESTORE test-project",
        db,
        7,
    )
    fourth = restored_second["restored_commit"]
    assert git(repo, "show", "HEAD:README.md") == "second"
    assert git(repo, "merge-base", "--is-ancestor", third, fourth) == ""
    assert git(repo, "rev-parse", f"{fourth}^{{tree}}") == git(
        repo, "rev-parse", f"{second}^{{tree}}"
    )


@pytest.mark.asyncio
async def test_restore_rejects_stale_preview_and_wrong_confirmation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "test-project"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "ELANORA test")
    git(repo, "config", "user.email", "test@elanora.local")
    first = commit_file(repo, "first\n", "Initial state")
    current = commit_file(repo, "second\n", "Accepted contribution")
    service = GitService(str(tmp_path))

    async def project_lookup(*_args: object) -> object:
        return SimpleNamespace(project_id=12, project_name="test-project")

    monkeypatch.setattr(
        "app.service.project_history.get_project_by_name", project_lookup
    )
    db = AsyncMock()

    with pytest.raises(ValueError, match="Type"):
        await service.restore_project_version(
            "test-project",
            first,
            current,
            "A sufficiently clear reason.",
            "test-project",
            db,
            7,
        )
    with pytest.raises(ValueError, match="Refresh the preview"):
        await service.restore_project_version(
            "test-project",
            first,
            "0" * 40,
            "A sufficiently clear reason.",
            "RESTORE test-project",
            db,
            7,
        )


@pytest.mark.asyncio
async def test_restore_resets_git_when_database_commit_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo = tmp_path / "test-project"
    repo.mkdir()
    git(repo, "init", "--initial-branch=main")
    git(repo, "config", "user.name", "ELANORA test")
    git(repo, "config", "user.email", "test@elanora.local")
    first = commit_file(repo, "first\n", "Initial state")
    current = commit_file(repo, "second\n", "Accepted contribution")
    service = GitService(str(tmp_path))
    service.rebuild_project_database = AsyncMock()

    async def project_lookup(*_args: object) -> object:
        return SimpleNamespace(project_id=12, project_name="test-project")

    monkeypatch.setattr(
        "app.service.project_history.get_project_by_name", project_lookup
    )
    monkeypatch.setattr(
        "app.service.project_history.get_pending_uploads", AsyncMock(return_value=[])
    )
    monkeypatch.setattr(
        "app.service.project_history.append_project_revision", AsyncMock()
    )
    monkeypatch.setattr(
        "app.service.project_history.update_backup", lambda *_args: None
    )
    db = AsyncMock()
    db.add = MagicMock()
    db.commit.side_effect = RuntimeError("simulated database commit failure")

    with pytest.raises(RuntimeError, match="simulated database commit failure"):
        await service.restore_project_version(
            "test-project",
            first,
            current,
            "Rollback this failed restoration.",
            "RESTORE test-project",
            db,
            7,
        )

    assert git(repo, "rev-parse", "HEAD") == current
    assert git(repo, "show", "HEAD:README.md") == "second"
    db.rollback.assert_awaited_once()
