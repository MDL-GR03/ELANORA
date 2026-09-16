"""Accepted project history, its health, and restoring it."""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import git_shared
from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
)
from app.dependency.user import get_admin_dep
from app.elan.validation import EafValidationError
from app.model.user import User
from app.schema.requests.git import (
    ProjectRevisionRecoveryRequest,
    ProjectVersionPreviewRequest,
    ProjectVersionRestoreRequest,
)
from app.schema.responses.git import (
    AcceptedProjectHistoryResponse,
    ProjectRevisionHealthResponse,
    ProjectRevisionRecoveryResponse,
    ProjectVersionPreviewResponse,
    ProjectVersionRestoreResponse,
)
from app.service.project_recovery import ProjectStorageIntactError

router = APIRouter()


@router.get(
    "/projects/{project_name}/accepted-history",
    response_model=AcceptedProjectHistoryResponse,
    dependencies=[get_project_admin_dep],
)
async def get_accepted_project_history(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> AcceptedProjectHistoryResponse:
    """List immutable versions from the project's canonical branch."""
    try:
        result = await git_shared.git_service.get_accepted_project_history(
            project_name, db
        )
        return AcceptedProjectHistoryResponse(**result)
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc


@router.get(
    "/projects/{project_name}/accepted-history/health",
    response_model=ProjectRevisionHealthResponse,
    dependencies=[get_project_admin_dep],
)
async def get_current_project_revision_health(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectRevisionHealthResponse:
    """Diagnose the current accepted EAF files and mutable database projection."""
    try:
        result = await git_shared.git_service.get_current_revision_health(
            project_name, db
        )
        return ProjectRevisionHealthResponse(**result)
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc


@router.post(
    "/projects/{project_name}/accepted-history/recover",
    response_model=ProjectRevisionRecoveryResponse,
    dependencies=[get_project_admin_dep, git_shared.project_lock_dep],
)
async def recover_current_project_revision(
    project_name: str,
    request: ProjectRevisionRecoveryRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectRevisionRecoveryResponse:
    """Repair the current accepted EAF state from its immutable ledger manifest."""
    try:
        result = await git_shared.git_service.recover_current_revision_from_manifest(
            project_name,
            request.revision_id,
            db,
            access.user.user_id,
            reason=request.reason,
            confirmation=request.confirmation,
        )
        return ProjectRevisionRecoveryResponse(**result)
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, RuntimeError, EafValidationError) as exc:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from exc


@router.post(
    "/projects/{project_name}/accepted-history/preview",
    response_model=ProjectVersionPreviewResponse,
    dependencies=[get_project_admin_dep],
)
async def preview_project_version_restore(
    project_name: str,
    request: ProjectVersionPreviewRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectVersionPreviewResponse:
    """Preview a restoration and its effect on current and pending work."""
    try:
        result = await git_shared.git_service.preview_project_version_restore(
            project_name, request.target_commit, db
        )
        return ProjectVersionPreviewResponse(**result)
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, EafValidationError) as exc:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from exc


@router.post(
    "/projects/{project_name}/accepted-history/restore",
    response_model=ProjectVersionRestoreResponse,
    dependencies=[get_project_admin_dep, git_shared.project_lock_dep],
)
async def restore_project_version(
    project_name: str,
    request: ProjectVersionRestoreRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectVersionRestoreResponse:
    """Restore an older tree as a new, fully audited canonical version."""
    try:
        result = await git_shared.git_service.restore_project_version(
            project_name,
            request.target_commit,
            request.expected_head,
            request.reason,
            request.confirmation,
            db,
            access.user.user_id,
            access.user.username,
        )
        return ProjectVersionRestoreResponse(**result)
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, EafValidationError) as exc:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from exc


@router.post(
    "/projects/{project_name}/restore-from-backup",
    dependencies=[git_shared.project_lock_dep],
)
async def restore_from_backup(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
    """Restore the project folder from the most recent backup and update the database."""
    try:
        result = await git_shared.git_service.restore_project_from_backup(
            project_name, db, user.user_id
        )
        return {"status": "success", "detail": result}
    except ElanoraError:
        raise
    except ProjectStorageIntactError as e:
        raise ElanoraError(ErrorCode.PROJECT_STORAGE_INTACT) from e
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.RECOVERY_BACKUP_NOT_FOUND) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/decline-backup",
    dependencies=[git_shared.project_lock_dep],
)
async def decline_backup(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> None:
    """Decline restoration of the most recent backup for the project, delete it and erase all related data from the database."""
    try:
        await git_shared.git_service.decline_project_backup(db, project_name)
    except ElanoraError:
        raise
    except ProjectStorageIntactError as e:
        raise ElanoraError(ErrorCode.PROJECT_STORAGE_INTACT) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/discard-local-changes",
    dependencies=[git_shared.project_lock_dep],
)
async def discard_local_changes(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
    """Preserve evidence, then reset the project folder to canonical Git state."""
    try:
        operation = await git_shared.sync_coordinator.discard(
            project_name, db, user.user_id
        )
        return {
            "status": "success",
            "detail": "Server-side changes discarded",
            "operation_id": str(operation.operation_id),
        }
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e
