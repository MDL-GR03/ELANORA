"""Read-only semantic and Git compatibility inspection for contributions."""

from datetime import datetime
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
    def duplicate_map(pending_uploads: list[Any], runner: GitCommandRunner) -> dict[int, int]:
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
                collisions.append(
                    {"contribution_id": other_id, "annotations": shared}
                )
        return sorted(collisions, key=lambda item: item["contribution_id"])

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

    def test_compatibility(
        self, project_name: str, branch_name: str
    ) -> dict[str, Any]:
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
            "tested_at": datetime.now().isoformat(),
        }
