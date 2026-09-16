"""Project-scoped authorization dependencies."""

from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.user import get_user_dep
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.enums import ProjectCapability, ProjectPermission, UserRole
from app.model.project import Project
from app.model.user import User

PERMISSION_LEVEL = {
    ProjectPermission.READ: 1,
    ProjectPermission.WRITE: 2,
    ProjectPermission.ADMIN: 3,
    ProjectPermission.OWNER: 4,
}


@dataclass(frozen=True, slots=True)
class ProjectAccess:
    """Authorized project context passed to an endpoint."""

    project: Project
    user: User
    permission: ProjectPermission


class ProjectGuard:
    """Resolve a path-scoped project and enforce the requested capability."""

    def __init__(self, required: ProjectPermission) -> None:
        self.required = required

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = get_db_dep,
        user: User = get_user_dep,
    ) -> ProjectAccess:
        project_id = request.path_params.get("project_id")
        project_name = request.path_params.get("project_name")
        if project_id is None and project_name is None:
            raise RuntimeError(
                "ProjectGuard requires project_id or project_name in the route"
            )

        return await authorize_project(
            db,
            user,
            self.required,
            project_id=int(project_id) if project_id is not None else None,
            project_name=str(project_name) if project_name is not None else None,
        )


async def authorize_project(
    db: AsyncSession,
    user: User,
    required: ProjectPermission,
    *,
    project_id: int | None = None,
    project_name: str | None = None,
) -> ProjectAccess:
    """Resolve and authorize a project when its identifier is not a path parameter."""
    statement = select(Project).where(Project.deleted_at.is_(None))
    if project_id is not None:
        statement = statement.where(Project.project_id == project_id)
    elif project_name is not None:
        statement = statement.where(Project.project_name == project_name)
    else:
        raise RuntimeError("Project authorization requires an identifier")
    project = (await db.execute(statement)).scalar_one_or_none()
    if project is None or user.instance_id != project.instance_id:
        raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)
    if user.role == UserRole.ADMIN:
        return ProjectAccess(project, user, ProjectPermission.OWNER)
    membership = await db.scalar(
        select(UserToProject).where(
            UserToProject.project_id == project.project_id,
            UserToProject.user_id == user.user_id,
        )
    )
    if membership is None:
        raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)
    permission = ProjectPermission(membership.permission)
    if PERMISSION_LEVEL[permission] < PERMISSION_LEVEL[required]:
        raise ElanoraError(ErrorCode.PROJECT_PERMISSION_REQUIRED)
    return ProjectAccess(project, user, permission)


class ProjectCapabilityGuard:
    """Require a delegated project capability without widening normal access."""

    def __init__(self, capability: ProjectCapability) -> None:
        self.capability = capability

    async def __call__(
        self,
        request: Request,
        db: AsyncSession = get_db_dep,
        user: User = get_user_dep,
    ) -> ProjectAccess:
        access = await ProjectGuard(ProjectPermission.READ)(request, db, user)
        if user.role == UserRole.ADMIN or access.permission == ProjectPermission.OWNER:
            return access
        grant = await db.scalar(
            select(ProjectCapabilityGrant).where(
                ProjectCapabilityGrant.project_id == access.project.project_id,
                ProjectCapabilityGrant.user_id == user.user_id,
                ProjectCapabilityGrant.capability == self.capability,
            )
        )
        if grant is None:
            raise ElanoraError(
                ErrorCode.PROJECT_CAPABILITY_REQUIRED, capability=self.capability.value
            )
        return access


get_project_read_dep = Depends(ProjectGuard(ProjectPermission.READ))
get_project_write_dep = Depends(ProjectGuard(ProjectPermission.WRITE))
get_project_admin_dep = Depends(ProjectGuard(ProjectPermission.ADMIN))
get_protocol_manager_dep = Depends(
    ProjectCapabilityGuard(ProjectCapability.MANAGE_PROTOCOLS)
)
