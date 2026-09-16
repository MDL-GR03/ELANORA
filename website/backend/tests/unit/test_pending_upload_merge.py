from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.service.git_command_runner import GitCommandRunner


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


def initialized_repository(tmp_path: Path) -> GitCommandRunner:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=main"], check=True)
    runner.run(["config", "user.name", "Test"], check=True)
    runner.run(["config", "user.email", "test@example.org"], check=True)
    (tmp_path / "session.eaf").write_text("accepted\n", encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "accepted"], check=True)
    return runner


def commit_submission(runner: GitCommandRunner, tmp_path: Path, content: str) -> None:
    runner.run(["checkout", "-b", "upload_42"], check=True)
    (tmp_path / "session.eaf").write_text(content, encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "submission"], check=True)
    runner.run(["checkout", "main"], check=True)


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
    runner = initialized_repository(tmp_path)
    commit_submission(runner, tmp_path, "submitted\n")

    result = runner.complete_pending_merge("upload_42", "auto")

    assert result["status"] == "resolved"
    assert (tmp_path / "session.eaf").read_text(encoding="utf-8") == "submitted\n"
    assert runner.get_current_branch() == "main"
    assert runner.run(["status", "--porcelain"], check=True).stdout == ""


def test_retry_after_git_commit_rebuilds_projection_without_second_commit(
    tmp_path: Path,
) -> None:
    runner = initialized_repository(tmp_path)
    commit_submission(runner, tmp_path, "submitted\n")
    runner.complete_pending_merge("upload_42", "auto")
    accepted_commit = runner.get_commit_hash()

    result = runner.complete_pending_merge("upload_42", "auto")

    assert result["status"] == "already_merged"
    assert runner.get_commit_hash() == accepted_commit


def test_auto_merge_conflict_does_not_mutate_the_shared_checkout(
    tmp_path: Path,
) -> None:
    runner = initialized_repository(tmp_path)
    commit_submission(runner, tmp_path, "submitted\n")
    (tmp_path / "session.eaf").write_text("new accepted\n", encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "new accepted"], check=True)
    accepted_commit = runner.get_commit_hash()

    with pytest.raises(ValueError, match="require resolution"):
        runner.complete_pending_merge("upload_42", "auto")

    assert runner.get_commit_hash() == accepted_commit
    assert runner.get_current_branch() == "main"
    assert (tmp_path / "session.eaf").read_text(encoding="utf-8") == "new accepted\n"
    assert runner.run(["status", "--porcelain"], check=True).stdout == ""


def test_explicit_incoming_strategy_resolves_and_commits_conflicts(
    tmp_path: Path,
) -> None:
    runner = initialized_repository(tmp_path)
    commit_submission(runner, tmp_path, "submitted\n")
    (tmp_path / "session.eaf").write_text("new accepted\n", encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "new accepted"], check=True)

    result = runner.complete_pending_merge("upload_42", "accept_incoming")

    assert result["status"] == "resolved"
    assert (tmp_path / "session.eaf").read_text(encoding="utf-8") == "submitted\n"
    assert runner.get_current_branch() == "main"


def test_explicit_current_strategy_keeps_the_accepted_file(tmp_path: Path) -> None:
    runner = initialized_repository(tmp_path)
    commit_submission(runner, tmp_path, "submitted\n")
    (tmp_path / "session.eaf").write_text("new accepted\n", encoding="utf-8")
    runner.run(["add", "session.eaf"], check=True)
    runner.run(["commit", "-m", "new accepted"], check=True)

    result = runner.complete_pending_merge("upload_42", "accept_current")

    assert result["status"] == "resolved"
    assert (tmp_path / "session.eaf").read_text(encoding="utf-8") == "new accepted\n"
    assert runner.get_current_branch() == "main"
