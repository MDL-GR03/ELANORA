"""Administrator decisions about pending researcher contributions."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project_by_name
from app.model.enums import Status
from app.model.pending_upload import PendingUpload
from app.model.research_topic import ResearchTopic, ResearchTopicTier
from app.service.contribution_inspection import ContributionInspectionService
from app.service.research_topics import require_distinct_topic_name


class ContributionReviewService:
    """Apply explicit administrator review decisions without publishing Git."""

    def __init__(self, inspection: ContributionInspectionService) -> None:
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
        upload_data = dict(details.get("upload_data") or {})
        context = dict(upload_data.get("research_context") or {})
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
                    ResearchTopicTier(tier_name=name)
                    for name in sorted(changed_tiers)
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
