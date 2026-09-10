from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.model.enums import Status
from app.service.contribution_review import ContributionReviewService


@pytest.mark.asyncio
async def test_admin_assigns_existing_topic_without_rewriting_research_summary() -> None:
    inspection = MagicMock()
    inspection.semantic_analysis.return_value = ({}, {}, {"Prosody"})
    service = ContributionReviewService(inspection)
    upload = SimpleNamespace(
        upload_id=17,
        project_id=3,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="pending",
        base_commit="base",
        git_details={
            "upload_data": {
                "research_context": {
                    "summary": "Corrected phrase-final prominence"
                }
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
        result = await service.assign_research_topic(
            "corpus", 17, 8, None, db
        )

    assert result["summary"] == "Corrected phrase-final prominence"
    assert result["declared_topic_id"] == 8
    assert result["declared_tiers"] == ["Prosody"]
    assert result["topic_review_status"] == "verified"
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_admin_must_choose_existing_or_new_topic_not_both() -> None:
    service = ContributionReviewService(MagicMock())
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
