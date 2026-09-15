"""Recording a project's data classification, legal basis, retention and hold."""

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent
from app.model.project import Project
from app.schema.project_governance import (
    ProjectDataGovernance,
    ProjectDataGovernanceResponse,
)

GOVERNED_FIELDS = tuple(ProjectDataGovernance.model_fields)


def project_governance(project: Project) -> ProjectDataGovernanceResponse:
    """The governance currently recorded for a project."""
    return ProjectDataGovernanceResponse(
        **{field: getattr(project, field) for field in GOVERNED_FIELDS},
        updated_at=project.governance_updated_at,
        updated_by=project.governance_updated_by,
    )


async def update_project_governance(
    db: AsyncSession,
    *,
    project: Project,
    governance: ProjectDataGovernance,
    actor_user_id: int,
) -> ProjectDataGovernanceResponse:
    """Replace a project's governance and audit the values before and after."""
    before = project_governance(project).model_dump(
        mode="json", include=set(GOVERNED_FIELDS)
    )
    after = governance.model_dump(mode="json")
    for field in GOVERNED_FIELDS:
        setattr(project, field, getattr(governance, field))
    project.governance_updated_at = datetime.now(UTC)
    project.governance_updated_by = actor_user_id
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="project.data_governance.updated",
            resource_type="project",
            resource_id=str(project.project_id),
            details={"before": before, "after": after},
        )
    )
    await db.flush()
    return project_governance(project)
