"""Request schemas for project-user association management."""

from pydantic import BaseModel

from app.model.enums import ProjectPermission


class AddUserToProjectRequest(BaseModel):
    """Request to add a user to a project."""

    user_id: int
    permission: ProjectPermission = ProjectPermission.READ


class UpdateUserPermissionRequest(BaseModel):
    """Request to update a user's permission in a project."""

    permission: ProjectPermission
