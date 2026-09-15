"""The canonical working tree is returned to its accepted branch before writes."""

from pathlib import Path

import pytest

from app.service.git_operations import (
    GitCommandRunner,
    WorkingTreeOffAcceptedBranchError,
)


def _repository(tmp_path: Path) -> GitCommandRunner:
    (tmp_path / "elan_files").mkdir()
    (tmp_path / "elan_files" / "session.eaf").write_text("accepted")
    runner = GitCommandRunner(tmp_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA checkout test"], check=True)
    runner.run(["config", "user.email", "checkout@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Accepted"], check=True)
    return runner


def _current_branch(runner: GitCommandRunner) -> str:
    return runner.run(["rev-parse", "--abbrev-ref", "HEAD"], check=True).stdout.strip()


def test_canonical_head_names_the_accepted_branch_whatever_is_checked_out(
    tmp_path: Path,
) -> None:
    runner = _repository(tmp_path)
    accepted = runner.get_commit_hash()
    runner.run(["checkout", "-b", "stray"], check=True)
    (tmp_path / "elan_files" / "stray.eaf").write_text("unaccepted")
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Stray"], check=True)

    assert runner.get_commit_hash() != accepted
    assert runner.canonical_head() == accepted


def test_a_clean_tree_on_a_stray_branch_is_returned_to_the_accepted_branch(
    tmp_path: Path,
) -> None:
    runner = _repository(tmp_path)
    runner.run(["checkout", "-b", "stray"], check=True)

    runner.ensure_canonical_checkout()

    assert _current_branch(runner) == "master"


def test_uncommitted_work_on_a_stray_branch_is_refused_not_carried_across(
    tmp_path: Path,
) -> None:
    """Those changes belong to whatever was interrupted, not the accepted branch."""
    runner = _repository(tmp_path)
    runner.run(["checkout", "-b", "upload_crashed_midway"], check=True)
    (tmp_path / "elan_files" / "half-written.eaf").write_text("interrupted")

    with pytest.raises(WorkingTreeOffAcceptedBranchError):
        runner.ensure_canonical_checkout()

    assert _current_branch(runner) == "upload_crashed_midway"
    assert (tmp_path / "elan_files" / "half-written.eaf").read_text() == "interrupted"


def test_a_tree_already_on_the_accepted_branch_is_left_alone(tmp_path: Path) -> None:
    """Uncommitted edits on the accepted branch are the synchronization flow's."""
    runner = _repository(tmp_path)
    (tmp_path / "elan_files" / "session.eaf").write_text("edited on the server")

    runner.ensure_canonical_checkout()

    assert _current_branch(runner) == "master"
    assert (
        tmp_path / "elan_files" / "session.eaf"
    ).read_text() == "edited on the server"
