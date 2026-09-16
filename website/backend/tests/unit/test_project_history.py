from pathlib import Path

import pytest

from app.service.git_command_runner import GitCommandRunner
from app.service.project_history import ProjectHistoryService


def _repository(path: Path) -> tuple[GitCommandRunner, str]:
    runner = GitCommandRunner(path, maintain_backup=False)
    runner.init_repo()
    (path / "README.md").write_text("accepted\n", encoding="utf-8")
    runner.add_all()
    runner.commit("Accepted project revision")
    return runner, runner.get_commit_hash()


def test_resolve_export_commit_accepts_canonical_revision(tmp_path: Path) -> None:
    runner, accepted = _repository(tmp_path)

    resolved, canonical = ProjectHistoryService().resolve_export_commit(
        runner, accepted[:10]
    )

    assert resolved == accepted
    assert canonical == [accepted]


def test_resolve_export_commit_rejects_unpublished_branch(tmp_path: Path) -> None:
    runner, _accepted = _repository(tmp_path)
    runner.run(["checkout", "-b", "unpublished"], check=True)
    (tmp_path / "README.md").write_text("unpublished\n", encoding="utf-8")
    runner.add_all()
    runner.commit("Unpublished branch revision")
    unpublished = runner.get_commit_hash()

    with pytest.raises(ValueError, match="not in accepted project history"):
        ProjectHistoryService().resolve_export_commit(runner, unpublished)


@pytest.mark.parametrize("value", ["", "../HEAD", "not-a-commit", "123456"])
def test_resolve_export_commit_rejects_unsafe_identifiers(
    tmp_path: Path, value: str
) -> None:
    runner, _accepted = _repository(tmp_path)

    with pytest.raises(ValueError, match="Invalid project version"):
        ProjectHistoryService().resolve_export_commit(runner, value)
