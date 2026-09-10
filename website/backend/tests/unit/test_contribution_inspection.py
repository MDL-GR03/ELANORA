from types import SimpleNamespace
from unittest.mock import MagicMock, patch

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


def test_research_scope_allows_configured_baseline_changes() -> None:
    service = ContributionInspectionService(MagicMock())
    project = SimpleNamespace(protocol_version_id="protocol-2")
    upload = SimpleNamespace(
        branch_name="pending",
        base_commit="base",
        git_details={
            "upload_data": {
                "protocol_validation": {
                    "outcome": "passed",
                    "protocol_version_id": "protocol-2",
                },
                "research_context": {
                    "summary": "Corrected prosodic phrasing",
                    "declared_tiers": ["Prosody"],
                },
            }
        },
    )

    with patch.object(
        service,
        "semantic_analysis",
        return_value=(
            {"files": 1},
            {"session.eaf": {"a1": ("value",)}},
            {"Prosody", "Sign-LH"},
        ),
    ):
        _, _, context, protocol, protocol_id = service.research_scope(
            "corpus", project, upload, {"Sign-LH"}
        )

    assert protocol == "passed"
    assert protocol_id == "protocol-2"
    assert context["scope_status"] == "aligned"
    assert context["baseline_changed_tiers"] == ["Sign-LH"]
    assert context["outside_scope_tiers"] == []


def test_research_scope_requires_protocol_recheck_after_protocol_change() -> None:
    service = ContributionInspectionService(MagicMock())
    project = SimpleNamespace(protocol_version_id="protocol-2")
    upload = SimpleNamespace(
        branch_name="pending",
        base_commit="base",
        git_details={
            "upload_data": {
                "protocol_validation": {
                    "outcome": "passed",
                    "protocol_version_id": "protocol-1",
                },
                "research_context": {"summary": "Checked the file"},
            }
        },
    )

    with patch.object(service, "semantic_analysis", return_value=({}, {}, set())):
        _, _, _, protocol, _ = service.research_scope(
            "corpus", project, upload, set()
        )

    assert protocol == "recheck_required"
