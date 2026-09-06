from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest

from app.service.git_operations import GitCommandRunner


def test_git_commands_trust_only_the_resolved_project_directory(
    tmp_path: Path,
) -> None:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)

    with patch(
        "app.service.git_operations.subprocess.run",
        return_value=CompletedProcess([], 0, stdout="", stderr=""),
    ) as run:
        runner.run(["status", "--porcelain"], check=True)

    command = run.call_args.args[0]
    assert command[:5] == [
        "git",
        "-c",
        f"safe.directory={tmp_path.resolve()}",
        "-c",
        "core.quotepath=false",
    ]
    assert command[5:] == ["status", "--porcelain"]


def test_get_status_does_not_hide_git_failures(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)

    with (
        patch.object(
            runner,
            "run",
            side_effect=RuntimeError("repository is unsafe"),
        ),
        pytest.raises(RuntimeError, match="repository is unsafe"),
    ):
        runner.get_status()


def test_get_tree_hash_uses_revision_content_identity(tmp_path: Path) -> None:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)

    with patch.object(
        runner,
        "run",
        return_value=CompletedProcess([], 0, stdout="tree-sha\n", stderr=""),
    ) as run:
        assert runner.get_tree_hash("submission") == "tree-sha"

    run.assert_called_once_with(
        ["rev-parse", "--verify", "submission^{tree}"], check=True
    )
