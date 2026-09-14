from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.model.enums import Status
from app.service.contribution_review import ContributionReviewService


@pytest.mark.asyncio
async def test_admin_assigns_existing_topic_without_rewriting_research_summary() -> (
    None
):
    inspection = MagicMock()
    inspection.semantic_analysis.return_value = ({}, {}, {"Prosody"})
    service = ContributionReviewService(MagicMock(), inspection)
    upload = SimpleNamespace(
        upload_id=17,
        project_id=3,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="pending",
        base_commit="base",
        git_details={
            "upload_data": {
                "research_context": {"summary": "Corrected phrase-final prominence"}
            }
        },
    )
    topic = SimpleNamespace(
        topic_id=8,
        name="Prosody",
        tiers=[SimpleNamespace(tier_name="Prosody")],
    )
    db = AsyncMock()
    db.get.return_value = upload
    db.scalar.return_value = topic

    with patch(
        "app.service.contribution_review.get_project_by_name",
        new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
    ):
        result = await service.assign_research_topic("corpus", 17, 8, None, db)

    assert result["summary"] == "Corrected phrase-final prominence"
    assert result["declared_topic_id"] == 8
    assert result["declared_tiers"] == ["Prosody"]
    assert result["topic_review_status"] == "verified"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_must_choose_existing_or_new_topic_not_both() -> None:
    service = ContributionReviewService(MagicMock(), MagicMock())
    upload = SimpleNamespace(
        project_id=3,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="pending",
    )
    db = AsyncMock()
    db.get.return_value = upload

    with (
        patch(
            "app.service.contribution_review.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        pytest.raises(ValueError, match="existing topic or create a new one"),
    ):
        await service.assign_research_topic("corpus", 17, 8, "Prosody", db)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_dismissal_requires_an_earlier_identical_tree(
    tmp_path: Path,
) -> None:
    service = ContributionReviewService(tmp_path, MagicMock())
    upload = SimpleNamespace(upload_id=17, branch_name="later")
    earlier = SimpleNamespace(upload_id=16, branch_name="earlier")
    db = AsyncMock()
    runner = MagicMock()
    runner.get_tree_hash.side_effect = ["later-tree", "earlier-tree"]

    with (
        patch(
            "app.service.contribution_review.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch(
            "app.service.contribution_review.get_pending_uploads",
            new=AsyncMock(return_value=[earlier, upload]),
        ),
        patch("app.service.contribution_review.GitCommandRunner", return_value=runner),
        pytest.raises(ValueError, match="not a duplicate"),
    ):
        await service.dismiss_duplicate("corpus", 17, db, 2)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_decline_requires_a_meaningful_reason(tmp_path: Path) -> None:
    service = ContributionReviewService(tmp_path, MagicMock())
    upload = SimpleNamespace(
        project_id=3,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="pending",
    )
    db = AsyncMock()
    db.get.return_value = upload

    with (
        patch(
            "app.service.contribution_review.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        pytest.raises(ValueError, match="decline reason"),
    ):
        await service.decline("corpus", 17, "  ", db, 2)

    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_superseded_contribution_is_not_eligible_for_acceptance(
    tmp_path: Path,
) -> None:
    service = ContributionReviewService(tmp_path, MagicMock())
    upload = SimpleNamespace(
        upload_id=17,
        branch_name="pending",
        superseded_by_upload_id=18,
    )
    db = AsyncMock()

    with (
        patch(
            "app.service.contribution_review.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch(
            "app.service.contribution_review.get_pending_uploads",
            new=AsyncMock(return_value=[upload]),
        ),
        pytest.raises(ValueError, match="superseded by contribution #18"),
    ):
        await service.require_acceptance_eligibility("corpus", "pending", db)


@pytest.mark.asyncio
async def test_proposed_topic_must_be_resolved_before_acceptance(
    tmp_path: Path,
) -> None:
    service = ContributionReviewService(tmp_path, MagicMock())
    upload = SimpleNamespace(
        upload_id=17,
        branch_name="pending",
        superseded_by_upload_id=None,
        git_details={
            "upload_data": {
                "research_context": {
                    "summary": "Updated prosodic phrasing",
                    "topic_review_status": "proposed",
                }
            }
        },
    )
    db = AsyncMock()

    with (
        patch(
            "app.service.contribution_review.get_project_by_name",
            new=AsyncMock(return_value=SimpleNamespace(project_id=3)),
        ),
        patch(
            "app.service.contribution_review.get_pending_uploads",
            new=AsyncMock(return_value=[upload]),
        ),
        pytest.raises(ValueError, match="Assign the proposed research topic"),
    ):
        await service.require_acceptance_eligibility("corpus", "pending", db)
