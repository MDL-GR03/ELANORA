from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.service.contribution_intake import (
    ContributionAlreadyCurrentError,
    ContributionIntakeService,
    DuplicatePendingContributionError,
    SubmissionContext,
)


def context() -> SubmissionContext:
    return SubmissionContext("researcher", 7, "base", {"status": "passed"}, {})


@pytest.mark.asyncio
async def test_current_project_tree_is_not_recorded_as_a_contribution() -> None:
    runner = MagicMock()
    runner.canonical_branch.return_value = "main"
    runner.get_tree_hash.return_value = "same-tree"

    with (
        patch(
            "app.service.contribution_intake.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch("app.service.contribution_intake.GitCommandRunner", return_value=runner),
        pytest.raises(ContributionAlreadyCurrentError),
    ):
        await ContributionIntakeService().record_pending_submission(
            MagicMock(), MagicMock(), "upload", AsyncMock(), context(), Path("project")
        )


@pytest.mark.asyncio
async def test_identical_pending_tree_names_the_existing_contribution() -> None:
    runner = MagicMock()
    runner.canonical_branch.return_value = "main"
    runner.get_tree_hash.side_effect = ["submitted", "accepted", "submitted"]

    with (
        patch(
            "app.service.contribution_intake.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch(
            "app.service.contribution_intake.get_pending_uploads",
            new=AsyncMock(
                return_value=[SimpleNamespace(branch_name="pending", upload_id=19)]
            ),
        ),
        patch("app.service.contribution_intake.GitCommandRunner", return_value=runner),
        pytest.raises(DuplicatePendingContributionError) as error,
    ):
        await ContributionIntakeService().record_pending_submission(
            MagicMock(), MagicMock(), "upload", AsyncMock(), context(), Path("project")
        )

    assert error.value.upload_id == 19


@pytest.mark.asyncio
async def test_pending_submission_records_provenance_and_renamed_branch() -> None:
    runner = MagicMock()
    runner.canonical_branch.return_value = "main"
    runner.get_tree_hash.side_effect = ["submitted", "accepted"]
    branch_manager = MagicMock()
    analyzer = MagicMock()
    analyzer.analyze_merge_differences.return_value = SimpleNamespace(
        new_files=["new.eaf"], modified_files=[], deleted_files=[]
    )
    save = AsyncMock(return_value=SimpleNamespace(upload_id=23))

    with (
        patch(
            "app.service.contribution_intake.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch(
            "app.service.contribution_intake.get_pending_uploads",
            new=AsyncMock(return_value=[]),
        ),
        patch("app.service.contribution_intake.save_pending_upload", new=save),
        patch("app.service.contribution_intake.GitCommandRunner", return_value=runner),
    ):
        result = await ContributionIntakeService().record_pending_submission(
            branch_manager,
            analyzer,
            "upload",
            AsyncMock(),
            context(),
            Path("project"),
        )

    assert result["upload_id"] == 23
    assert result["branch_name"] == "upload_pending_approval"
    assert result["new_files"] == ["new.eaf"]
    branch_manager.switch_to_master.assert_called_once()
    save.assert_awaited_once()
    saved_call = save.await_args
    assert saved_call is not None
    assert saved_call.kwargs["submitted_by"] == 7
    assert saved_call.kwargs["base_commit"] == "base"
