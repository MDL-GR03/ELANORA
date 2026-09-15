"""Per-project data governance endpoints."""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
)
from app.schema.project_governance import (
    ProjectDataGovernance,
    ProjectDataGovernanceResponse,
)
from app.service.project_governance import (
    project_governance,
    update_project_governance,
)

router = APIRouter()


@router.get(
    "/projects/{project_id}/data-governance",
    response_model=ProjectDataGovernanceResponse,
)
async def read_data_governance(
    access: ProjectAccess = get_project_read_dep,
) -> ProjectDataGovernanceResponse:
    """Members can see how their project's data is classified and kept."""
    return project_governance(access.project)


@router.put(
    "/projects/{project_id}/data-governance",
    response_model=ProjectDataGovernanceResponse,
)
async def replace_data_governance(
    request: ProjectDataGovernance,
    access: ProjectAccess = get_project_admin_dep,
    db: AsyncSession = get_db_dep,
) -> ProjectDataGovernanceResponse:
    """Only project administrators classify data and set retention or holds."""
    result = await update_project_governance(
        db,
        project=access.project,
        governance=request,
        actor_user_id=access.user.user_id,
    )
    await db.commit()
    return result
