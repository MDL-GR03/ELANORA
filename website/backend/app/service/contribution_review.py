"""Administrator decisions about pending researcher contributions."""

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.pending_upload import get_pending_uploads
from app.crud.project import get_project_by_name
from app.model.audit_event import AuditEvent
from app.model.enums import ReviewCaseState, Status
from app.model.notification import Notification
from app.model.pending_upload import PendingUpload
from app.model.research_topic import ResearchTopic, ResearchTopicTier
from app.model.review import ReviewCase
from app.service.contribution_inspection import ContributionInspectionService
from app.service.eaf_review import validate_repository_eafs
from app.service.git_operations import GitCommandRunner
from app.service.protocol import (
    get_pinned_protocol_version,
)
from app.service.protocol_evaluation import (
    blocking_findings,
    validate_content_against_protocol,
)
from app.service.research_topics import require_distinct_topic_name
from app.storage.paths import safe_project_path

logger = get_logger()


def _object_dict(value: object) -> dict[str, Any]:
    """Copy JSON object data while rejecting unexpected persisted shapes."""
    return dict(value) if isinstance(value, dict) else {}


MIN_DECLINE_REASON_LENGTH = 3


class ContributionReviewService:
    """Apply explicit administrator review decisions without publishing Git."""

    def __init__(
        self, base_path: Path, inspection: ContributionInspectionService
    ) -> None:
        self.base_path = base_path
        self.inspection = inspection

    async def assign_research_topic(
        self,
        project_name: str,
        upload_id: int,
        topic_id: int | None,
        new_topic_name: str | None,
        db: AsyncSession,
    ) -> dict[str, Any]:
        """Assign an existing topic or explicitly approve a proposed new topic."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError("Project not found")
        upload = await db.get(PendingUpload, upload_id)
        if (
            upload is None
            or upload.project_id != project.project_id
            or upload.status != Status.PENDING_ADMIN_APPROVAL
            or not upload.branch_name
        ):
            raise FileNotFoundError("Pending contribution not found")
        if topic_id is not None and new_topic_name:
            raise ValueError("Choose an existing topic or create a new one, not both")

        details = dict(upload.git_details or {})
        upload_data = _object_dict(details.get("upload_data"))
        context = _object_dict(upload_data.get("research_context"))
        _, _, changed_tiers = self.inspection.semantic_analysis(
            project_name, upload.branch_name, upload_data, upload.base_commit
        )

        topic = None
        if topic_id is not None:
            topic = await db.scalar(
                select(ResearchTopic).where(
                    ResearchTopic.topic_id == topic_id,
                    ResearchTopic.project_id == project.project_id,
                )
            )
            if topic is None:
                raise ValueError("Research topic not found")
        elif new_topic_name:
            cleaned_name = " ".join(new_topic_name.split())
            project_topics = list(
                (
                    await db.scalars(
                        select(ResearchTopic).where(
                            ResearchTopic.project_id == project.project_id
                        )
                    )
                ).all()
            )
            require_distinct_topic_name(cleaned_name, project_topics)
            if not changed_tiers:
                raise ValueError(
                    "A topic cannot be created because no changed tiers were detected"
                )
            topic = ResearchTopic(
                project_id=project.project_id,
                name=cleaned_name,
                description=f"Created while classifying contribution #{upload.upload_id}.",
                allow_new_tiers=False,
                tiers=[
                    ResearchTopicTier(tier_name=name) for name in sorted(changed_tiers)
                ],
            )
            db.add(topic)
            await db.flush()

        context.update(
            {
                "declared_topic_id": topic.topic_id if topic else None,
                "declared_topic_name": topic.name if topic else None,
                "declared_tiers": (
                    sorted(item.tier_name for item in topic.tiers) if topic else []
                ),
                "proposed_topic_name": None,
                "topic_review_status": "verified",
                "topic_match": "administrator_decision",
            }
        )
        upload_data["research_context"] = context
        details["upload_data"] = upload_data
        upload.git_details = details
        await db.commit()
        return context

    async def dismiss_duplicate(
        self, project_name: str, upload_id: int, db: AsyncSession, user_id: int
    ) -> dict[str, Any]:
        """Dismiss a verified duplicate while retaining its audit record."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending = await get_pending_uploads(db, project.project_id)
        upload = next((item for item in pending if item.upload_id == upload_id), None)
        if upload is None or not upload.branch_name:
            raise FileNotFoundError("Pending contribution not found")

        runner = GitCommandRunner(safe_project_path(self.base_path, project_name))
        submitted_tree = runner.get_tree_hash(upload.branch_name)
        original = next(
            (
                item
                for item in sorted(pending, key=lambda item: item.upload_id)
                if item.upload_id < upload.upload_id
                and item.branch_name
                and runner.get_tree_hash(item.branch_name) == submitted_tree
            ),
            None,
        )
        if original is None:
            raise ValueError(
                "This contribution is not a duplicate of an earlier pending contribution"
            )

        upload.status = Status.DISMISSED
        upload.resolved_at = datetime.now()
        upload.resolved_by = user_id
        db.add(
            AuditEvent(
                actor_user_id=user_id,
                project_id=project.project_id,
                action="contribution.duplicate_dismissed",
                resource_type="pending_upload",
                resource_id=str(upload.upload_id),
                details={"duplicate_of_upload_id": original.upload_id},
            )
        )
        if upload.submitted_by not in {None, user_id}:
            db.add(
                Notification(
                    user_id=upload.submitted_by,
                    title="Duplicate contribution dismissed",
                    message=(
                        f"Your contribution to {project_name} matched contribution "
                        f"#{original.upload_id}; no research data was lost."
                    ),
                    action_url=f"/contribution?project={project.project_id}",
                )
            )
        await db.commit()
        try:
            runner.delete_branch_localy(upload.branch_name)
        except Exception as error:
            logger.error(
                "Could not remove a dismissed duplicate contribution branch; "
                "error_type=%s",
                safe_exception_type(error),
            )
        return {
            "status": "dismissed",
            "upload_id": upload.upload_id,
            "duplicate_of_upload_id": original.upload_id,
        }

    async def decline(
        self,
        project_name: str,
        upload_id: int,
        reason: str,
        db: AsyncSession,
        user_id: int,
    ) -> dict[str, Any]:
        """Terminally decline pending work without erasing its audit history."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        upload = await db.get(PendingUpload, upload_id)
        if (
            upload is None
            or upload.project_id != project.project_id
            or upload.status != Status.PENDING_ADMIN_APPROVAL
            or not upload.branch_name
        ):
            raise FileNotFoundError("Pending contribution not found")

        decline_reason = reason.strip()
        if len(decline_reason) < MIN_DECLINE_REASON_LENGTH:
            raise ValueError("A decline reason is required")
        now = datetime.now()
        upload.status = Status.DISMISSED
        upload.resolved_at = now
        upload.resolved_by = user_id
        review_cases = list(
            (
                await db.scalars(
                    select(ReviewCase).where(
                        ReviewCase.project_id == project.project_id,
                        (
                            (ReviewCase.upload_id == upload.upload_id)
                            | (ReviewCase.resubmitted_upload_id == upload.upload_id)
                        ),
                        ReviewCase.state.not_in(
                            [ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED]
                        ),
                    )
                )
            ).all()
        )
        for review_case in review_cases:
            review_case.state = ReviewCaseState.CLOSED
            review_case.resolved_at = now
            review_case.updated_at = now
        db.add(
            AuditEvent(
                actor_user_id=user_id,
                project_id=project.project_id,
                action="contribution.declined",
                resource_type="pending_upload",
                resource_id=str(upload.upload_id),
                details={
                    "branch_name": upload.branch_name,
                    "reason": decline_reason,
                    "closed_review_case_ids": [
                        str(review_case.case_id) for review_case in review_cases
                    ],
                },
            )
        )
        if upload.submitted_by not in {None, user_id}:
            db.add(
                Notification(
                    user_id=upload.submitted_by,
                    title="Contribution declined",
                    message=(
                        f"Your contribution to {project_name} was declined: "
                        f"{decline_reason}"
                    ),
                    action_url=f"/contribution?project={project.project_id}",
                )
            )
        await db.commit()
        try:
            GitCommandRunner(
                safe_project_path(self.base_path, project_name)
            ).delete_branch_localy(upload.branch_name)
        except Exception as error:
            logger.error(
                "Could not remove a declined contribution branch; error_type=%s",
                safe_exception_type(error),
            )
        return {"status": "dismissed", "upload_id": upload.upload_id}

    async def require_acceptance_eligibility(
        self,
        project_name: str,
        branch_name: str,
        db: AsyncSession,
    ) -> tuple[Any, PendingUpload, Any]:
        """Reject publication until every administrator decision is resolved."""
        project = await get_project_by_name(db, project_name)
        if project is None:
            raise FileNotFoundError(f"Project '{project_name}' not found")
        pending = await get_pending_uploads(db, project.project_id)
        upload = next(
            (item for item in pending if item.branch_name == branch_name), None
        )
        if upload is None:
            raise FileNotFoundError("Pending contribution not found")
        if upload.superseded_by_upload_id is not None:
            raise ValueError(
                f"Contribution #{upload.upload_id} was superseded by "
                f"contribution #{upload.superseded_by_upload_id} and cannot be accepted"
            )

        upload_data = _object_dict((upload.git_details or {}).get("upload_data"))
        context = _object_dict(upload_data.get("research_context"))
        if context:
            if not str(context.get("summary") or "").strip():
                raise ValueError(
                    "The researcher must describe the work before this contribution can be merged"
                )
            if context.get("topic_review_status") == "proposed":
                raise ValueError(
                    "Assign the proposed research topic before merging this contribution"
                )

        blocking_review = await db.scalar(
            select(ReviewCase.case_id).where(
                ReviewCase.project_id == project.project_id,
                (
                    (ReviewCase.upload_id == upload.upload_id)
                    | (ReviewCase.resubmitted_upload_id == upload.upload_id)
                ),
                ReviewCase.state.in_(
                    [
                        ReviewCaseState.OPEN.value,
                        ReviewCaseState.CHANGES_REQUESTED.value,
                        ReviewCaseState.RESUBMITTED.value,
                    ]
                ),
            )
        )
        if blocking_review is not None:
            raise ValueError(
                "Resolve the contribution's open review cases before accepting it"
            )

        project_path = safe_project_path(self.base_path, project_name)
        submitted_eafs = validate_repository_eafs(project_path, branch_name)
        protocol = await get_pinned_protocol_version(db, project)
        protocol_errors = [
            (filename, finding)
            for filename, content in submitted_eafs.items()
            for finding in (
                blocking_findings(validate_content_against_protocol(content, protocol))
                if protocol is not None
                else ()
            )
        ]
        if protocol_errors:
            filename, finding = protocol_errors[0]
            additional = len(protocol_errors) - 1
            suffix = f" and {additional} more issue(s)" if additional else ""
            raise ValueError(
                f"{filename}: {finding.message}{suffix}. "
                "Correct the file in ELAN and submit it again."
            )
        return project, upload, protocol
