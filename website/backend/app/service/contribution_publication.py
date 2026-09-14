"""Publication of administrator-approved contribution revisions."""

from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.pending_upload import mark_upload_processed
from app.model.audit_event import AuditEvent
from app.model.notification import Notification
from app.service.contribution_review import ContributionReviewService
from app.service.git_operations import GitCommandRunner
from app.service.project_revision import append_project_revision
from app.storage.paths import safe_project_path
from app.utils.project_backup import update_backup

ProjectionRebuilder = Callable[[str, AsyncSession, int], Awaitable[None]]


class ContributionPublicationService:
    """Publish eligible work and keep Git, projection, ledger, and audit aligned."""

    def __init__(self, base_path: Path, review: ContributionReviewService) -> None:
        self.base_path = base_path
        self.review = review

    async def publish(
        self,
        project_name: str,
        branch_name: str,
        resolution_strategy: str,
        db: AsyncSession,
        user_id: int,
        rebuild_projection: ProjectionRebuilder,
        expected_parent_commit: str | None = None,
    ) -> dict[str, Any]:
        """Publish one reviewed contribution as a new accepted revision."""
        (
            project,
            pending_upload,
            protocol,
        ) = await self.review.require_acceptance_eligibility(
            project_name, branch_name, db
        )
        project_path = safe_project_path(self.base_path, project_name)
        runner = GitCommandRunner(project_path)
        parent_commit = expected_parent_commit or runner.get_commit_hash()
        result = runner.complete_pending_merge(branch_name, resolution_strategy)
        accepted_commit = runner.get_commit_hash()
        try:
            await rebuild_projection(project_name, db, user_id)
            await mark_upload_processed(
                db,
                project.project_id,
                branch_name,
                user_id,
                accepted_commit,
            )
            await append_project_revision(
                db,
                project_id=project.project_id,
                git_commit=accepted_commit,
                parent_git_commit=parent_commit,
                source_type="contribution",
                actor_user_id=user_id,
                contribution_id=pending_upload.upload_id,
                details={
                    "branch_name": branch_name,
                    "base_commit": pending_upload.base_commit or "",
                    "resolution_strategy": resolution_strategy,
                },
            )
            db.add(
                AuditEvent(
                    actor_user_id=user_id,
                    project_id=project.project_id,
                    action="contribution.accepted",
                    resource_type="pending_upload",
                    resource_id=str(pending_upload.upload_id),
                    details={
                        "branch_name": branch_name,
                        "base_commit": pending_upload.base_commit,
                        "accepted_commit": accepted_commit,
                        "resolution_strategy": resolution_strategy,
                        "merge_status": result["status"],
                        "protocol_version_id": (
                            str(protocol.protocol_version_id)
                            if protocol is not None
                            else None
                        ),
                    },
                )
            )
            if pending_upload.submitted_by not in {None, user_id}:
                db.add(
                    Notification(
                        user_id=pending_upload.submitted_by,
                        title="Contribution accepted",
                        message=(
                            f"Your contribution to {project_name} is now part of "
                            "the project."
                        ),
                        action_url=f"/contribution?project={project.project_id}",
                    )
                )
            await db.commit()
        except Exception:
            await db.rollback()
            runner.reset_hard(parent_commit)
            update_backup(project_path.name, project_path.parent)
            raise
        runner.delete_branch_localy(branch_name)
        update_backup(project_path.name, project_path.parent)
        return {
            "project_name": project_name,
            **result,
            "accepted_commit": accepted_commit,
            "resolved_at": datetime.now().isoformat(),
        }
