"""Creating, listing, editing and deleting projects."""

from typing import Any

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import git_shared
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.elan_validation import validate_and_record_elan_files
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
)
from app.dependency.user import get_admin_dep, get_user_dep
from app.model.user import User
from app.schema.requests.git import (
    ContributionPolicyRequest,
    ProjectCreateRequest,
    ProjectEditRequest,
)
from app.schema.responses.git import (
    GitStatusResponse,
    ProjectCreateResponse,
    ProjectEditResponse,
    ProjectFilesResponse,
    ProjectFilesWithMediaResponse,
    ProjectListResponse,
)
from app.service.project_lifecycle import ProjectNameUnavailableError

router = APIRouter()


@router.get("/check", response_model=GitStatusResponse)
async def check_git(user: User = get_admin_dep) -> GitStatusResponse:
    """Check if Git is available on the system.

    Args:
        user: Authenticated admin user.

    Returns:
        GitStatusResponse: Git availability status, version, and any errors.

    Raises:
        ElanoraError: 500 if Git check fails.

    """
    try:
        result = git_shared.git_service.check_git_availability()
        return GitStatusResponse(**result)
    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post("/projects/create", response_model=ProjectCreateResponse)
async def create_project(
    project_data: ProjectCreateRequest,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> ProjectCreateResponse:
    """Create a new ELAN project with Git repository.

    Args:
        project_data: Project creation request containing project name.
        user: Authenticated admin user.

    Returns:
        ProjectCreateResponse: Details of the created project including path and Git status.

    Raises:
        ElanoraError: 400 if project already exists, 500 if creation fails.

    """
    try:
        result = await git_shared.git_service.create_project(
            project_data.project_name,
            project_data.description,
            db,
            user.user_id,
            user.instance_id,
        )
        return ProjectCreateResponse(**result)
    except ElanoraError:
        raise
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_OPERATION_INVALID) from e
    except Exception as e:
        git_shared.logger.error(
            "Unable to create a project; error_type=%s", safe_exception_type(e)
        )
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> ProjectListResponse:
    """List all project names for the current instance (admin only)."""
    projects = await git_shared.git_service.list_projects(db, user.instance_id)
    return ProjectListResponse(projects=projects)


@router.get("/user-projects", response_model=ProjectListResponse)
async def list_user_projects(
    db: AsyncSession = get_db_dep,
    user: User = get_user_dep,
) -> ProjectListResponse:
    """List project names that the current user has access to."""
    projects = await git_shared.git_service.list_user_projects(
        db, user.user_id, user.instance_id
    )
    return ProjectListResponse(projects=projects)


@router.post("/projects/init-from-folder-upload", response_model=ProjectCreateResponse)
async def init_project_from_folder_upload(
    project_name: str = Form(...),
    description: str = Form(...),
    files: list[UploadFile] = git_shared.eaf_upload_files_dep,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> ProjectCreateResponse:
    """Initialize a project from EAF files that pass the normal upload boundary."""
    validated_batch = await validate_and_record_elan_files(
        files,
        db=db,
        instance_id=user.instance_id,
        project_id=None,
        requested_project_name=project_name,
        submitted_by=user.user_id,
    )
    try:
        result = await git_shared.git_service.init_project_from_folder_upload(
            project_name,
            description,
            validated_batch.files,
            db,
            user.user_id,
            user.instance_id,
        )
        return ProjectCreateResponse(**result)
    except (HTTPException, ElanoraError):
        raise
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_OPERATION_INVALID) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get("/projects/{project_name}/files")
async def get_project_files(
    project_name: str,
    include_media: bool = False,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> ProjectFilesResponse | ProjectFilesWithMediaResponse:
    """Get project files, optionally with media information.

    Args:
        project_name: Name of the project
        include_media: Whether to include media filenames for each file
        db: Database session
        user: Authenticated admin user

    Returns:
        ProjectFilesResponse or ProjectFilesWithMediaResponse depending on include_media

    """
    try:
        result = await git_shared.git_service.list_project_files(
            project_name, db, include_media
        )
        response_type = (
            ProjectFilesWithMediaResponse if include_media else ProjectFilesResponse
        )
        return response_type(**result)
    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get("/projects/{project_name}/branches")
async def get_project_branches(
    project_name: str, user: User = get_admin_dep
) -> dict[str, Any]:
    """Get all branches for a project."""
    try:
        result = git_shared.git_service.get_branches(project_name)
        return result
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_FILE_NOT_FOUND) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.delete("/projects/{project_name}", dependencies=[git_shared.project_lock_dep])
async def delete_project(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
    """Delete a project, its files, and all associated database artifacts."""
    try:
        await git_shared.git_service.delete_project(project_name, db)
        return {"status": "success", "detail": f"Project '{project_name}' deleted."}
    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/edit",
    response_model=ProjectEditResponse,
    dependencies=[git_shared.project_lock_dep],
)
async def edit_project(
    project_name: str,
    req: ProjectEditRequest,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> ProjectEditResponse:
    try:
        result = await git_shared.git_service.edit_project(
            project_name, req.new_project_name, req.new_project_description, db
        )
        return ProjectEditResponse(**result)
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_FILE_NOT_FOUND) from e
    except ProjectNameUnavailableError as e:
        raise ElanoraError(ErrorCode.PROJECT_NAME_UNAVAILABLE) from e
    except FileExistsError as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.put("/projects/{project_id}/contribution-policy")
async def update_contribution_policy(
    project_id: int,
    request: ContributionPolicyRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, bool]:
    """Configure the deliberately narrow safe automatic-acceptance policy."""
    access.project.auto_accept_new_files = request.auto_accept_new_files
    await db.commit()
    return {"auto_accept_new_files": access.project.auto_accept_new_files}
