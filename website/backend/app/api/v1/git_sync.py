"""Reconciling a project's Git export with its accepted revision."""

import uuid
from typing import Any

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import git_shared
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.elan.validation import EafValidationError
from app.model.user import User
from app.schema.responses.git import (
    ProjectSyncCheckResponse,
    ProjectSyncExecutionResponse,
)
from app.service.project_sync import operation_payload

router = APIRouter()


@router.get(
    "/projects/{project_name}/synchronize/check",
    response_model=ProjectSyncCheckResponse,
    dependencies=[git_shared.project_lock_dep],
)
async def synchronize_project_check(
    project_name: str,
    user: User = get_admin_dep,
) -> ProjectSyncCheckResponse:
    """Preview unmanaged server-side EAF changes without modifying the repository."""
    try:
        return ProjectSyncCheckResponse(
            **git_shared.git_service.synchronize_project_check(project_name)
        )
    except ElanoraError:
        raise
    except Exception as e:
        git_shared.logger.error(
            "Failed to inspect server-side project changes; error_type=%s",
            safe_exception_type(e),
        )
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/synchronize",
    response_model=ProjectSyncExecutionResponse,
    dependencies=[git_shared.project_lock_dep],
)
async def synchronize_project(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> ProjectSyncExecutionResponse:
    """Synchronize the project's elan_files folder with the git repo and update the database.

    Only changed, added, or deleted files are processed.
    """
    try:
        operation = await git_shared.sync_coordinator.execute(
            project_name, db, user.user_id
        )
        return ProjectSyncExecutionResponse(
            project_name=project_name,
            in_sync=operation.state == "completed",
            files_status=operation.changes,
            status=operation.state,
            operation_id=str(operation.operation_id),
        )
    except ElanoraError:
        raise
    except (EafValidationError, ValueError) as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_INVALID) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get(
    "/projects/{project_name}/synchronize/operations",
    dependencies=[git_shared.project_lock_dep],
)
async def list_synchronization_operations(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, list[dict[str, Any]]]:
    """Return the durable administrator recovery history for one project."""
    try:
        operations = await git_shared.sync_coordinator.list_for_project(
            project_name, db
        )
        return {"operations": [operation_payload(item) for item in operations]}
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e


@router.post(
    "/projects/{project_name}/synchronize/operations/{operation_id}/recover",
    dependencies=[git_shared.project_lock_dep],
)
async def recover_synchronization_operation(
    project_name: str,
    operation_id: uuid.UUID,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, Any]:
    """Reconcile PostgreSQL from a Git commit left by an interrupted operation."""
    try:
        operation = await git_shared.sync_coordinator.recover(
            project_name, operation_id, db, user.user_id
        )
        return operation_payload(operation)
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from e
