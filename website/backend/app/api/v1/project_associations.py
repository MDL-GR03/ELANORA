"""API endpoints for managing project-user associations (admin only)."""

import logging
from typing import Any, cast

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.crud.association import (
    get_project_users,
    remove_user_from_project,
)
from app.crud.project import (
    add_user_to_project,
    list_projects_by_user,
    update_user_project_permission,
    user_in_project,
)
from app.crud.user import get_all_active_users, get_user_by_id
from app.dependency.database import get_db_dep
from app.dependency.project_access import ProjectAccess, get_project_admin_dep
from app.dependency.user import get_admin_dep
from app.model.enums import ProjectPermission
from app.model.user import User
from app.schema.requests.project_association import (
    AddUserToProjectRequest,
    UpdateUserPermissionRequest,
)
from app.schema.responses.project_association import (
    ProjectAssociationResponse,
    ProjectUserListResponse,
    UserProjectListResponse,
)
from app.schema.responses.user import UserListResponse, UserResponse
from app.service.notification import NotificationService

router = APIRouter()

# Constants to avoid duplication


def _reject_reserved_or_escalated_permission(
    access: ProjectAccess, requested: ProjectPermission
) -> None:
    """Keep owner virtual and prevent project admins granting peer authority."""
    if requested == ProjectPermission.OWNER:
        raise ElanoraError(ErrorCode.OWNER_PERMISSION_RESERVED)
    if (
        access.permission == ProjectPermission.ADMIN
        and requested == ProjectPermission.ADMIN
    ):
        raise ElanoraError(ErrorCode.PROJECT_ADMIN_GRANT_FORBIDDEN)


async def _protect_privileged_target(
    db: AsyncSession, access: ProjectAccess, target_user_id: int
) -> None:
    if access.permission != ProjectPermission.ADMIN:
        return
    membership = await user_in_project(db, target_user_id, access.project.project_id)
    if membership and ProjectPermission(membership.permission) in {
        ProjectPermission.ADMIN,
        ProjectPermission.OWNER,
    }:
        raise ElanoraError(ErrorCode.PROJECT_ADMIN_CHANGE_FORBIDDEN)


@router.get("/projects/{project_id}/users", response_model=ProjectUserListResponse)
async def list_project_users(
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectUserListResponse:
    """List members for a project administered by the caller."""
    try:
        users = await get_project_users(db, access.project.project_id)

        # Institution administrators can manage every project without an
        # explicit membership row. Include the current administrator so they
        # can also be selected as the lead of a review they manage.
        if all(item["user_id"] != access.user.user_id for item in users):
            users.append(
                {
                    "user_id": access.user.user_id,
                    "username": access.user.username,
                    "email": access.user.email,
                    "permission": ProjectPermission.OWNER,
                    "capabilities": [],
                }
            )

        return ProjectUserListResponse(
            project_name=access.project.project_name,
            users=cast(list[Any], [
                {
                    "user_id": user_info["user_id"],
                    "username": user_info["username"],
                    "email": user_info["email"],
                    "permission": user_info["permission"],
                    "capabilities": user_info["capabilities"],
                }
                for user_info in users
            ]),
        )
    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get("/projects/{project_id}/available-users", response_model=UserListResponse)
async def list_available_project_users(
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> UserListResponse:
    """List same-institution candidates for an administered project."""
    users = await get_all_active_users(db, access.project.instance_id)
    return UserListResponse(users=[UserResponse.model_validate(user) for user in users])


@router.get("/users/{user_id}/projects", response_model=UserProjectListResponse)
async def list_user_projects_admin(
    user_id: int,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> UserProjectListResponse:
    """List all projects associated with a specific user (admin only)."""
    try:
        # check if the user exists
        target_user = await get_user_by_id(db, user_id)
        if not target_user or target_user.instance_id != user.instance_id:
            raise ElanoraError(ErrorCode.USER_NOT_FOUND)

        # Retrieve the user's projects
        projects = await list_projects_by_user(
            db, user_id, instance_id=target_user.instance_id
        )

        return UserProjectListResponse(
            user_id=user_id,
            username=target_user.username,
            projects=cast(list[Any], [
                {
                    "project_id": project.project_id,
                    "project_name": project.project_name,
                    "description": project.description,
                }
                for project in projects
            ]),
        )
    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post("/projects/{project_id}/users", response_model=ProjectAssociationResponse)
async def add_user_to_project_admin(
    request: AddUserToProjectRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectAssociationResponse:
    """Add a user to a project administered by the caller."""
    try:
        _reject_reserved_or_escalated_permission(access, request.permission)
        target_user = await get_user_by_id(db, request.user_id)
        if not target_user or target_user.instance_id != access.project.instance_id:
            raise ElanoraError(ErrorCode.USER_NOT_FOUND)

        # Add the user to the project
        association = await add_user_to_project(
            db=db,
            user_id=request.user_id,
            project_id=access.project.project_id,
            permission=request.permission,
        )

        return ProjectAssociationResponse(
            project_name=access.project.project_name,
            user_id=request.user_id,
            username=target_user.username,
            permission=association.permission,
            message=f"User {target_user.username} added to project {access.project.project_name}",
        )

    except ValueError as e:
        raise ElanoraError(ErrorCode.MEMBERSHIP_INVALID) from e
    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.put(
    "/projects/{project_id}/users/{user_id}",
    response_model=ProjectAssociationResponse,
)
async def update_user_project_permission_admin(
    user_id: int,
    request: UpdateUserPermissionRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectAssociationResponse:
    """Update member access for a project administered by the caller."""
    try:
        _reject_reserved_or_escalated_permission(access, request.permission)
        await _protect_privileged_target(db, access, user_id)
        target_user = await get_user_by_id(db, user_id)
        if not target_user or target_user.instance_id != access.project.instance_id:
            raise ElanoraError(ErrorCode.USER_NOT_FOUND)

        # Update the user's permission
        association = await update_user_project_permission(
            db=db,
            user_id=user_id,
            project_id=access.project.project_id,
            permission=request.permission,
        )

        if not association:
            raise ElanoraError(ErrorCode.USER_NOT_IN_PROJECT)

        # Send notification and email about role change
        admin_name = f"{access.user.first_name} {access.user.last_name}"
        try:
            _, _ = await NotificationService.send_role_change_notification_and_email(
                db=db,
                user_id=user_id,
                user_email=target_user.email,
                username=target_user.username,
                project_name=access.project.project_name,
                new_role=str(request.permission.value),
                project_id=access.project.project_id,
                admin_name=admin_name,
                language="fr",  # You could get this from user preferences or request
            )
        except Exception as e:
            # Log the error but don't fail the permission update
            logging.warning(
                "Failed to send role change notification; error_type=%s",
                type(e).__name__,
            )

        # Commit the changes
        await db.commit()

        return ProjectAssociationResponse(
            project_name=access.project.project_name,
            user_id=user_id,
            username=target_user.username,
            permission=association.permission,
            message=f"User {target_user.username} permission updated to {request.permission} in project {access.project.project_name}",
        )

    except ValueError as e:
        raise ElanoraError(ErrorCode.MEMBERSHIP_INVALID) from e
    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.delete(
    "/projects/{project_id}/users/{user_id}",
    response_model=ProjectAssociationResponse,
)
async def remove_user_from_project_admin(
    user_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectAssociationResponse:
    """Remove a member from a project administered by the caller."""
    try:
        await _protect_privileged_target(db, access, user_id)
        target_user = await get_user_by_id(db, user_id)
        if not target_user or target_user.instance_id != access.project.instance_id:
            raise ElanoraError(ErrorCode.USER_NOT_FOUND)

        await remove_user_from_project(db, user_id, access.project.project_id)

        return ProjectAssociationResponse(
            project_name=access.project.project_name,
            user_id=user_id,
            username=target_user.username,
            permission=None,
            message=f"User {target_user.username} removed from project {access.project.project_name}",
        )

    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e
