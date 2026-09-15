"""Read-only semantic and Git compatibility inspection for contributions."""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.centralized_logging import get_logger
from app.elan.validation import EafValidationError
from app.service.eaf_review import EafReviewUnavailableError, compare_repository_eaf
from app.service.git_operations import GitCommandRunner
from app.storage.paths import safe_project_path

logger = get_logger()


class ContributionInspectionService:
    """Inspect submitted revisions without changing accepted project state."""

    def __init__(self, base_path: Path) -> None:
        self.base_path = base_path

    @staticmethod
    def duplicate_map(
        pending_uploads: list[Any], runner: GitCommandRunner
    ) -> dict[int, int]:
        """Map later pending uploads to the earliest identical submitted tree."""
        tree_groups: dict[str, list[int]] = {}
        for upload in pending_uploads:
            if not upload.branch_name:
                continue
            try:
                tree_hash = runner.get_tree_hash(upload.branch_name)
                tree_groups.setdefault(tree_hash, []).append(upload.upload_id)
            except Exception:
                logger.warning(
                    "Could not determine content identity for contribution %s",
                    upload.upload_id,
                )
        return {
            upload_id: min(upload_ids)
            for upload_ids in tree_groups.values()
            for upload_id in upload_ids
            if upload_id != min(upload_ids)
        }

    @staticmethod
    def annotation_collisions(
        upload_id: int,
        targets_by_upload: dict[int, dict[str, dict[str, tuple[Any, ...]]]],
        candidate_ids: set[int],
    ) -> list[dict[str, Any]]:
        """Describe differing edits to the same annotation in active submissions."""
        if upload_id not in candidate_ids:
            return []
        targets = targets_by_upload.get(upload_id, {})
        collisions: list[dict[str, Any]] = []
        for other_id, other_targets in targets_by_upload.items():
            if other_id == upload_id or other_id not in candidate_ids:
                continue
            shared: dict[str, list[str]] = {}
            for filename in targets.keys() & other_targets.keys():
                differing_ids = sorted(
                    annotation_id
                    for annotation_id in targets[filename].keys()
                    & other_targets[filename].keys()
                    if targets[filename][annotation_id]
                    != other_targets[filename][annotation_id]
                )
                if differing_ids:
                    shared[filename] = differing_ids
            if shared:
                collisions.append({"contribution_id": other_id, "annotations": shared})
        return sorted(collisions, key=lambda item: item["contribution_id"])

    def research_scope(
        self,
        project_name: str,
        project: Any,
        upload: Any,
        configured_baseline_tiers: set[str],
    ) -> tuple[
        dict[str, int],
        dict[str, dict[str, tuple[Any, ...]]],
        dict[str, Any],
        str,
        str | None,
    ]:
        """Evaluate protocol freshness and declared research scope for one upload."""
        git_details = upload.git_details or {}
        upload_data = git_details.get("upload_data", git_details)
        protocol_validation = upload_data.get("protocol_validation") or {}
        current_protocol_id = (
            str(project.protocol_version_id)
            if project.protocol_version_id is not None
            else None
        )
        recorded_protocol_id = protocol_validation.get("protocol_version_id")
        protocol_outcome = (
            "not_configured"
            if current_protocol_id is None
            else (
                "passed"
                if protocol_validation.get("outcome") == "passed"
                and recorded_protocol_id == current_protocol_id
                else "recheck_required"
            )
        )
        if not upload.branch_name:
            raise ValueError("Pending contribution has no review branch")
        semantic_summary, semantic_targets, changed_tiers = self.semantic_analysis(
            project_name, upload.branch_name, upload_data, upload.base_commit
        )
        research_context = dict(upload_data.get("research_context") or {})
        declared_tiers = {
            tier
            for tier in research_context.get("declared_tiers", [])
            if isinstance(tier, str)
        }
        baseline_tiers = configured_baseline_tiers | {
            tier
            for tier in research_context.get("baseline_tiers", [])
            if isinstance(tier, str)
        }
        outside_scope = sorted(changed_tiers - declared_tiers - baseline_tiers)
        research_context.update(
            {
                "changed_tiers": sorted(changed_tiers),
                "baseline_changed_tiers": sorted(changed_tiers & baseline_tiers),
                "outside_scope_tiers": outside_scope,
                "scope_status": (
                    "missing_context"
                    if not research_context.get("summary")
                    else "topic_review_needed"
                    if research_context.get("topic_review_status") == "proposed"
                    else "outside_scope"
                    if declared_tiers and outside_scope
                    else "aligned"
                    if declared_tiers
                    else "declared_general"
                ),
            }
        )
        return (
            semantic_summary,
            semantic_targets,
            research_context,
            protocol_outcome,
            recorded_protocol_id,
        )

    @staticmethod
    def queue_item(
        upload: Any,
        upload_data: dict[str, Any],
        semantic_summary: dict[str, int],
        research_context: dict[str, Any],
        protocol_outcome: str,
        recorded_protocol_id: str | None,
        merge_status: str,
        **extra: Any,
    ) -> dict[str, Any]:
        """Build the stable administrator queue representation for one upload."""
        branch_name = upload.branch_name
        item = {
            "upload_id": upload.upload_id,
            "branch_name": branch_name,
            "original_branch": upload_data.get(
                "original_branch",
                branch_name.replace("_pending_approval", "") if branch_name else None,
            ),
            "upload_type": upload.upload_type.value,
            "description": upload.upload_description,
            "status": upload.status.value,
            "uploaded_at": (
                upload.detected_at.isoformat() if upload.detected_at else None
            ),
            "uploaded_by": upload_data.get("uploaded_by"),
            "files": {
                "new": upload_data.get("new_files", []),
                "modified": upload_data.get("modified_files", []),
                "deleted": upload_data.get("deleted_files", []),
            },
            "file_counts": {
                "new": upload_data.get("new_files_count", 0),
                "modified": upload_data.get("modified_files_count", 0),
                "deleted": upload_data.get("deleted_files_count", 0),
            },
            "quality_checks": {
                "eaf": "passed",
                "naming": "passed",
                "protocol": protocol_outcome,
            },
            "protocol_warnings": list(
                (upload_data.get("protocol_validation") or {}).get("warnings") or []
            ),
            "semantic_summary": semantic_summary,
            "research_context": research_context,
            "protocol_version_id": recorded_protocol_id,
            "git_details": upload.git_details,
            "merge_status": merge_status,
        }
        item.update(extra)
        return item

    @staticmethod
    def inspection_error_item(
        upload: Any, upload_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Return a deliberately sparse queue item when Git inspection fails."""
        branch_name = upload.branch_name
        return {
            "upload_id": upload.upload_id,
            "branch_name": branch_name,
            "original_branch": upload_data.get(
                "original_branch",
                branch_name.replace("_pending_approval", "") if branch_name else None,
            ),
            "upload_type": upload.upload_type.value,
            "description": upload.upload_description,
            "status": upload.status.value,
            "uploaded_at": (
                upload.detected_at.isoformat() if upload.detected_at else None
            ),
            "uploaded_by": None,
            "merge_status": "error",
            "error": "Unable to inspect this pending upload",
            "can_auto_merge": False,
        }

    def semantic_analysis(
        self,
        project_name: str,
        branch_name: str,
        upload_data: dict[str, Any],
        base_commit: str | None,
    ) -> tuple[dict[str, int], dict[str, dict[str, tuple[Any, ...]]], set[str]]:
        """Summarize EAF changes and retain targets for concurrency warnings."""
        filenames = {
            filename
            for key in ("new_files", "modified_files", "deleted_files")
            for filename in upload_data.get(key, [])
            if filename.lower().endswith(".eaf")
        }
        summary = {
            "files": 0,
            "annotations": 0,
            "added": 0,
            "removed": 0,
            "value_changed": 0,
            "timing_changed": 0,
            "tier_changed": 0,
            "reference_changed": 0,
            "media_changed": 0,
        }
        targets: dict[str, dict[str, tuple[Any, ...]]] = {}
        changed_tiers: set[str] = set()
        for filename in sorted(filenames):
            try:
                comparison = compare_repository_eaf(
                    self.base_path,
                    project_name,
                    branch_name,
                    filename,
                    accepted_revision=base_commit,
                )
            except (FileNotFoundError, EafReviewUnavailableError, EafValidationError):
                logger.warning(
                    "Could not summarize semantic changes for %s on %s",
                    filename,
                    branch_name,
                )
                continue
            summary["files"] += 1
            summary["annotations"] += len(comparison.changes)
            targets[filename] = {}
            for change in comparison.changes:
                after = change.after
                if change.before is not None:
                    changed_tiers.add(change.before.tier_id)
                if after is not None:
                    changed_tiers.add(after.tier_id)
                targets[filename][change.annotation_id] = (
                    tuple(change.kinds),
                    after.tier_id if after else None,
                    after.value if after else None,
                    after.start_ms if after else None,
                    after.end_ms if after else None,
                    after.annotation_ref if after else None,
                )
                for kind in change.kinds:
                    summary[kind.value] += 1
            if comparison.before_media_urls != comparison.after_media_urls:
                summary["media_changed"] += 1
        return summary, targets, changed_tiers

    def test_compatibility(self, project_name: str, branch_name: str) -> dict[str, Any]:
        """Preview Git compatibility without retaining working-tree changes."""
        project_path = safe_project_path(self.base_path, project_name)
        if not project_path.exists():
            raise FileNotFoundError(f"Project '{project_name}' not found")
        readiness = GitCommandRunner(project_path).preview_merge(branch_name)
        return {
            "status": readiness.status,
            "conflicted_files": readiness.conflicted_files,
            "conflicts_count": len(readiness.conflicted_files),
            "can_auto_merge": readiness.can_merge,
            "tested_at": datetime.now(UTC).isoformat(),
        }
