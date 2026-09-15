"""Durable coordination for publishing reviewed contributions."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any, cast

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from sqlalchemy.engine import CursorResult

from app.core.error_diagnostics import safe_failure_summary
from app.crud.project import get_project_by_name
from app.model.audit_event import AuditEvent
from app.model.contribution_change_set import ContributionChangeSet
from app.model.enums import Status
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.service.git import GitService
from app.service.git_operations import GitCommandRunner
from app.storage.paths import safe_project_path

MAX_PUBLICATION_ATTEMPTS = 10
INTERRUPTED_OPERATION_LEASE = timedelta(hours=1)


class ContributionChangeSetCoordinator:
    """Persist publication intent and execute it through an idempotent use case."""

    def __init__(self, git_service: GitService) -> None:
        self.git_service = git_service

    async def request(
        self,
        db: AsyncSession,
        *,
        project_name: str,
        branch_name: str,
        resolution_strategy: str,
        requested_by: int,
    ) -> ContributionChangeSet:
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        upload = await db.scalar(
            select(PendingUpload).where(
                PendingUpload.project_id == project.project_id,
                PendingUpload.branch_name == branch_name,
            )
        )
        if upload is None:
            raise FileNotFoundError("Contribution not found")

        existing = await db.scalar(
            select(ContributionChangeSet).where(
                ContributionChangeSet.upload_id == upload.upload_id
            )
        )
        if existing is not None:
            if existing.state in {"review_needed", "failed"}:
                project_path = safe_project_path(
                    self.git_service.base_path, project_name
                )
                existing.expected_commit = GitCommandRunner(
                    project_path, maintain_backup=False
                ).canonical_head()
                existing.requested_by = requested_by
                existing.resolution_strategy = resolution_strategy
                existing.state = "queued"
                existing.error = None
                await db.commit()
            return existing
        if upload.status not in {
            Status.PENDING_ADMIN_APPROVAL,
            Status.READY_TO_MERGE,
            Status.NEEDS_RESOLUTION,
            Status.BEING_REVIEWED,
        }:
            raise ValueError("Contribution is no longer awaiting publication")

        project_path = safe_project_path(self.git_service.base_path, project_name)
        # Guard the accepted branch itself, not whatever happens to be checked out.
        expected_commit = GitCommandRunner(
            project_path, maintain_backup=False
        ).canonical_head()
        change_set = ContributionChangeSet(
            project_id=project.project_id,
            upload_id=upload.upload_id,
            requested_by=requested_by,
            branch_name=branch_name,
            resolution_strategy=resolution_strategy,
            expected_commit=expected_commit,
            state="queued",
        )
        db.add(change_set)
        db.add(
            AuditEvent(
                actor_user_id=requested_by,
                project_id=project.project_id,
                action="contribution.publication_requested",
                resource_type="contribution_change_set",
                resource_id=str(change_set.change_set_id),
                details={
                    "upload_id": upload.upload_id,
                    "branch_name": branch_name,
                    "expected_commit": expected_commit,
                    "resolution_strategy": resolution_strategy,
                },
            )
        )
        await db.commit()
        return change_set

    async def execute(
        self, db: AsyncSession, change_set_id: uuid.UUID
    ) -> dict[str, Any]:
        change_set = await db.scalar(
            select(ContributionChangeSet)
            .where(ContributionChangeSet.change_set_id == change_set_id)
            .with_for_update()
        )
        if change_set is None:
            raise FileNotFoundError("Contribution change set not found")
        if change_set.state == "completed":
            return self._completed_payload(change_set)
        if change_set.state == "running":
            return self._change_set_payload(change_set)

        upload = await db.get(PendingUpload, change_set.upload_id)
        if upload is None:
            await self._mark_failed(
                db, change_set, "Contribution record is unavailable"
            )
            raise FileNotFoundError("Contribution not found")
        if upload.status == Status.RESOLVED and upload.accepted_commit:
            change_set.state = "completed"
            change_set.resulting_commit = upload.accepted_commit
            change_set.error = None
            change_set.completed_at = datetime.now(UTC)
            await db.commit()
            return self._completed_payload(change_set)

        project = await db.get(Project, change_set.project_id)
        if project is None:
            await self._mark_failed(db, change_set, "Project record is unavailable")
            raise FileNotFoundError("Project not found")
        if change_set.requested_by is None:
            await self._mark_failed(
                db, change_set, "Requesting administrator is unavailable"
            )
            raise ValueError(
                "The administrator who requested publication is unavailable"
            )
        project_path = safe_project_path(
            self.git_service.base_path, project.project_name
        )
        current_commit = GitCommandRunner(
            project_path, maintain_backup=False
        ).canonical_head()
        if current_commit != change_set.expected_commit:
            contribution_already_published = (
                GitCommandRunner(project_path, maintain_backup=False)
                .run(
                    [
                        "merge-base",
                        "--is-ancestor",
                        change_set.branch_name,
                        "HEAD",
                    ],
                    check=False,
                )
                .returncode
                == 0
            )
            if not contribution_already_published:
                change_set.state = "review_needed"
                change_set.error = (
                    "The accepted project changed after publication was requested; "
                    "review this contribution against the current version"
                )
                await db.commit()
                raise ValueError(change_set.error)
        change_set.state = "running"
        change_set.attempts += 1
        change_set.error = None
        await db.commit()
        try:
            result = await self.git_service.complete_pending_upload(
                project.project_name,
                change_set.branch_name,
                change_set.resolution_strategy,
                db,
                change_set.requested_by,
                expected_parent_commit=change_set.expected_commit,
            )
        except ValueError as error:
            await db.rollback()
            refreshed = await db.get(ContributionChangeSet, change_set_id)
            if refreshed is not None:
                refreshed.state = "review_needed"
                refreshed.error = safe_failure_summary(
                    error, operation="Contribution publication requires review"
                )
                await db.commit()
            raise
        except Exception:
            await db.rollback()
            refreshed = await db.get(ContributionChangeSet, change_set_id)
            if refreshed is not None:
                refreshed.state = "failed"
                refreshed.error = "Publication failed and can be retried"
                await db.commit()
            raise

        refreshed = await db.get(ContributionChangeSet, change_set_id)
        if refreshed is None:
            raise RuntimeError("Contribution change set disappeared during publication")
        refreshed.state = "completed"
        refreshed.resulting_commit = str(result["accepted_commit"])
        refreshed.error = None
        refreshed.completed_at = datetime.now(UTC)
        await db.commit()
        return {**result, **self._change_set_payload(refreshed)}

    async def next_retryable_id(self, db: AsyncSession) -> uuid.UUID | None:
        """Return the oldest queued or transiently failed publication request."""
        return cast(
            "uuid.UUID | None",
            await db.scalar(
                select(ContributionChangeSet.change_set_id)
                .where(
                    ContributionChangeSet.state.in_({"queued", "failed"}),
                    ContributionChangeSet.attempts < MAX_PUBLICATION_ATTEMPTS,
                )
                .order_by(
                    ContributionChangeSet.created_at,
                    ContributionChangeSet.change_set_id,
                )
                .limit(1)
            ),
        )

    async def requeue_interrupted(self, db: AsyncSession) -> int:
        """Requeue operations whose worker lease expired before an outcome."""
        cutoff = datetime.now(UTC) - INTERRUPTED_OPERATION_LEASE
        result = await db.execute(
            update(ContributionChangeSet)
            .where(
                ContributionChangeSet.state == "running",
                ContributionChangeSet.updated_at < cutoff,
                ContributionChangeSet.attempts < MAX_PUBLICATION_ATTEMPTS,
            )
            .values(
                state="failed",
                error="The previous publication worker stopped before recording an outcome",
                updated_at=datetime.now(UTC),
            )
        )
        await db.commit()
        return int(cast("CursorResult[Any]", result).rowcount or 0)

    async def _mark_failed(
        self, db: AsyncSession, change_set: ContributionChangeSet, message: str
    ) -> None:
        change_set.state = "failed"
        change_set.error = message
        await db.commit()

    @staticmethod
    def _change_set_payload(change_set: ContributionChangeSet) -> dict[str, str]:
        return {
            "change_set_id": str(change_set.change_set_id),
            "change_set_state": change_set.state,
        }

    @classmethod
    def _completed_payload(cls, change_set: ContributionChangeSet) -> dict[str, Any]:
        return {
            **cls._change_set_payload(change_set),
            "project_id": change_set.project_id,
            "branch_name": change_set.branch_name,
            "resolution_strategy": change_set.resolution_strategy,
            "accepted_commit": change_set.resulting_commit,
        }
