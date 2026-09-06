from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.service.git_operations import GitCommandRunner


class RecordingRunner(GitCommandRunner):
    def __init__(
        self, project_path: Path, *, conflicts: list[str], already_merged: bool = False
    ) -> None:
        super().__init__(project_path, maintain_backup=False)
        self.commands: list[tuple[list[str], bool]] = []
        self.conflicts = conflicts
        self.already_merged = already_merged

    def run(self, args: list[str], check: bool = False) -> Any:
        self.commands.append((args, check))
        if args[:2] == ["merge-base", "--is-ancestor"]:
            return SimpleNamespace(
                returncode=0 if self.already_merged else 1, stdout=""
            )
        return SimpleNamespace(returncode=1 if self.conflicts else 0, stdout="")

    def get_conflicted_files(self) -> list[str]:
        return self.conflicts

    def canonical_branch(self) -> str:
        return "master"


class PreviewRunner(GitCommandRunner):
    def __init__(self, project_path: Path, result: Any) -> None:
        super().__init__(project_path, maintain_backup=False)
        self.result = result
        self.commands: list[list[str]] = []

    def run(self, args: list[str], check: bool = False) -> Any:
        self.commands.append(args)
        return self.result

    def canonical_branch(self) -> str:
        return "master"


def test_merge_preview_is_non_mutating_and_reports_clean_result(tmp_path: Path) -> None:
    runner = PreviewRunner(
        tmp_path, SimpleNamespace(returncode=0, stdout="tree-id\n", stderr="")
    )

    result = runner.preview_merge("upload_42")

    assert result.can_merge
    assert runner.commands == [
        ["merge-tree", "--write-tree", "--name-only", "master", "upload_42"]
    ]


def test_merge_preview_reports_conflicted_files_without_checkout(
    tmp_path: Path,
) -> None:
    runner = PreviewRunner(
        tmp_path,
        SimpleNamespace(
            returncode=1,
            stdout="tree-id\nelan_files/session.eaf\n\nCONFLICT (content)\n",
            stderr="",
        ),
    )

    result = runner.preview_merge("upload_42")

    assert result.status == "needs_resolution"
    assert result.conflicted_files == ["elan_files/session.eaf"]


def test_real_merge_preview_supports_main_without_switching_branches(
    tmp_path: Path,
) -> None:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=main"], check=True)
    runner.run(["config", "user.name", "Test"], check=True)
    runner.run(["config", "user.email", "test@example.org"], check=True)
    source = tmp_path / "README.md"
    source.write_text("accepted\n", encoding="utf-8")
    runner.run(["add", "README.md"], check=True)
    runner.run(["commit", "-m", "accepted"], check=True)
    runner.run(["checkout", "-b", "submission"], check=True)
    (tmp_path / "session.eaf").write_text("<ANNOTATION_DOCUMENT />\n", encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "submission"], check=True)
    runner.run(["checkout", "main"], check=True)

    result = runner.preview_merge("submission")

    assert result.can_merge
    current = runner.run(["branch", "--show-current"], check=True)
    assert current.stdout.strip() == "main"
    assert not (tmp_path / "session.eaf").exists()


def test_clean_pending_contribution_is_committed_after_review(tmp_path: Path) -> None:
    runner = RecordingRunner(tmp_path, conflicts=[])

    result = runner.complete_pending_merge("upload_42", "auto")

    assert result["status"] == "resolved"
    assert (["merge", "--no-commit", "--no-ff", "upload_42"], False) in runner.commands
    assert (["add", "--all"], True) in runner.commands
    assert not any(
        command[:2] == ["merge", "--abort"] for command, _ in runner.commands
    )


def test_retry_after_git_commit_rebuilds_projection_without_second_commit(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(tmp_path, conflicts=[], already_merged=True)

    result = runner.complete_pending_merge("upload_42", "auto")

    assert result["status"] == "already_merged"
    assert not any(command[0] == "commit" for command, _ in runner.commands)


def test_auto_merge_aborts_without_committing_when_conflicts_exist(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(tmp_path, conflicts=["elan_files/session.eaf"])

    with pytest.raises(ValueError, match="require resolution"):
        runner.complete_pending_merge("upload_42", "auto")

    assert (["merge", "--abort"], False) in runner.commands
    assert not any(command[0] == "commit" for command, _ in runner.commands)


def test_explicit_incoming_strategy_resolves_and_commits_conflicts(
    tmp_path: Path,
) -> None:
    runner = RecordingRunner(tmp_path, conflicts=["elan_files/session.eaf"])

    runner.complete_pending_merge("upload_42", "accept_incoming")

    assert (["checkout", "--theirs", "--", "."], True) in runner.commands
    assert any(command[0] == "commit" for command, _ in runner.commands)
