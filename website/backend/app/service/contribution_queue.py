"""The administrator's review queue of pending contributions.

Building the queue inspects every pending contribution against the accepted
project: its declared research scope, whether it duplicates or supersedes
another submission, whether it still merges cleanly, and which annotations it
edits in common with other active submissions.

Each contribution is inspected in isolation. A record that cannot be inspected
is shown as an error item rather than failing the request, because one bad
submission must never hide every other contribution from the administrator.
"""

from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.pending_upload import get_pending_uploads
from app.crud.project import get_project_by_name
from app.model.research_topic import ProjectBaselineTier
from app.service.contribution_inspection import ContributionInspectionService
from app.service.git_operations import GitCommandRunner
from app.storage.paths import safe_project_path

logger = get_logger()

SemanticTargets = dict[str, dict[str, tuple[Any, ...]]]


class ContributionQueueService:
    """Compose the review queue from per-contribution inspection results."""

    def __init__(
        self, base_path: Path, inspection: ContributionInspectionService
    ) -> None:
        self.base_path = base_path
        self.inspection = inspection

    @staticmethod
    def _upload_data(upload: Any) -> dict[str, Any]:
        """Return the recorded submission details, tolerating malformed rows."""
        git_details = upload.git_details or {}
        raw = git_details.get("upload_data", git_details)
        return dict(raw) if isinstance(raw, dict) else {}

    async def _baseline_tiers(self, db: AsyncSession, project_id: int) -> set[str]:
        return set(
            (
                await db.scalars(
                    select(ProjectBaselineTier.tier_name).where(
                        ProjectBaselineTier.project_id == project_id
                    )
                )
            ).all()
        )

    async def review_queue(self, project_name: str, db: AsyncSession) -> dict[str, Any]:
        """List pending contributions with their merge readiness, computed now."""
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)

        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending_uploads = await get_pending_uploads(db, project.project_id)
        baseline_tiers = await self._baseline_tiers(db, project.project_id)

        duplicate_of = self.inspection.duplicate_map(pending_uploads, runner)
        collision_candidate_ids = {
            upload.upload_id
            for upload in pending_uploads
            if upload.superseded_by_upload_id is None
            and upload.upload_id not in duplicate_of
        }

        items: list[dict[str, Any]] = []
        targets_by_upload: dict[int, SemanticTargets] = {}
        ready_count = 0
        conflicts_count = 0

        for upload in pending_uploads:
            upload_data = self._upload_data(upload)
            try:
                (
                    semantic_summary,
                    semantic_targets,
                    research_context,
                    protocol_outcome,
                    recorded_protocol_id,
                ) = self.inspection.research_scope(
                    project_name, project, upload, baseline_tiers
                )
            except Exception as error:
                logger.warning(
                    "Could not evaluate a contribution's research scope; "
                    "upload_id=%s error_type=%s",
                    upload.upload_id,
                    safe_exception_type(error),
                )
                items.append(self.inspection.inspection_error_item(upload, upload_data))
                continue

            targets_by_upload[upload.upload_id] = semantic_targets
            describe = partial(
                self.inspection.queue_item,
                upload,
                upload_data,
                semantic_summary,
                research_context,
                protocol_outcome,
                recorded_protocol_id,
            )

            if upload.superseded_by_upload_id is not None:
                items.append(
                    describe(
                        "superseded",
                        superseded_by_upload_id=upload.superseded_by_upload_id,
                    )
                )
                continue

            if upload.upload_id in duplicate_of:
                items.append(
                    describe(
                        "duplicate",
                        duplicate_of_upload_id=duplicate_of[upload.upload_id],
                    )
                )
                continue

            try:
                readiness = runner.preview_merge(upload.branch_name)
                items.append(
                    describe(
                        readiness.status,
                        conflicted_files=readiness.conflicted_files,
                        conflicted_files_count=len(readiness.conflicted_files),
                        tested_at=datetime.now().isoformat(),
                    )
                )
            except Exception as error:
                logger.warning(
                    "Could not preview a contribution merge; "
                    "upload_id=%s error_type=%s",
                    upload.upload_id,
                    safe_exception_type(error),
                )
                items.append(self.inspection.inspection_error_item(upload, upload_data))
                continue

            if readiness.can_merge:
                ready_count += 1
            else:
                conflicts_count += 1

        for item in items:
            item["annotation_collisions"] = self.inspection.annotation_collisions(
                int(item["upload_id"]), targets_by_upload, collision_candidate_ids
            )

        return {
            "project_name": project_name,
            "pending_uploads": items,
            "total_pending": len(items),
            "ready_count": ready_count,
            "conflicts_count": conflicts_count,
        }
