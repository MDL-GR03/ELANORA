from types import SimpleNamespace
from unittest.mock import MagicMock

from app.service.contribution_inspection import ContributionInspectionService


def test_duplicate_map_uses_earliest_identical_pending_contribution() -> None:
    uploads = [
        SimpleNamespace(upload_id=14, branch_name="first"),
        SimpleNamespace(upload_id=15, branch_name="different"),
        SimpleNamespace(upload_id=16, branch_name="same-as-first"),
    ]
    runner = MagicMock()
    runner.get_tree_hash.side_effect = ["tree-a", "tree-b", "tree-a"]

    assert ContributionInspectionService.duplicate_map(uploads, runner) == {16: 14}


def test_annotation_collisions_only_report_different_results_for_same_target() -> None:
    targets = {
        14: {"session.eaf": {"a1": ("value", "Prosody", "one")}},
        15: {"session.eaf": {"a1": ("value", "Prosody", "two")}},
        16: {"session.eaf": {"a1": ("value", "Prosody", "one")}},
    }

    assert ContributionInspectionService.annotation_collisions(
        14, targets, {14, 15, 16}
    ) == [{"contribution_id": 15, "annotations": {"session.eaf": ["a1"]}}]
    assert ContributionInspectionService.annotation_collisions(
        14, targets, {15, 16}
    ) == []
