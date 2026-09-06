"""Response schemas for project-user association management."""

from pydantic import BaseModel, Field

from app.model.enums import ProjectPermission


class ProjectUserInfo(BaseModel):
    """Information about a user associated with a project."""

    user_id: int
    username: str
    email: str
    permission: ProjectPermission
    capabilities: list[str] = Field(default_factory=list)


class UserProjectInfo(BaseModel):
    """Information about a project associated with a user."""

    project_id: int
    project_name: str
    description: str


class ProjectAssociationResponse(BaseModel):
    """Response for project-user association operations."""

    project_name: str
    user_id: int
    username: str
    permission: ProjectPermission | None
    message: str


class ProjectUserListResponse(BaseModel):
    """Response containing list of users for a project."""

    project_name: str
    users: list[ProjectUserInfo]


class UserProjectListResponse(BaseModel):
    """Response containing list of projects for a user."""

    user_id: int
    username: str
    projects: list[UserProjectInfo]
