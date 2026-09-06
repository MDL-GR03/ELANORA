import uuid
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.dependency.database import get_db_dep
from app.dependency.elan_validation import validate_and_record_elan_files
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
    get_project_write_dep,
)
from app.dependency.project_lock import project_write_lock
from app.dependency.user import get_admin_dep, get_user_dep
from app.elan.validation import EafValidationError
from app.model.project import Project
from app.model.user import User
from app.schema.requests.git import (
    BulkRenameRequest,
    CommitRequest,
    ContributionPolicyRequest,
    PendingUploadMergeRequest,
    ProjectCheckoutRequest,
    ProjectCreateRequest,
    ProjectEditRequest,
)
from app.schema.responses.git import (
    BatchFileUploadResponse,
    BulkRenameResponse,
    CommitResponse,
    EafReviewResponse,
    FileRenameResponse,
    GitStatusResponse,
    PendingUploadsResponse,
    ProjectCheckoutResponse,
    ProjectCreateResponse,
    ProjectEditResponse,
    ProjectListResponse,
    ProjectSyncCheckResponse,
    ProjectSyncExecutionResponse,
)
from app.service.eaf_review import (
    EafReviewUnavailableError,
    compare_repository_eaf,
    comparison_payload,
)
from app.service.git import (
    ContributionAlreadyCurrentError,
    DuplicatePendingContributionError,
    GitService,
    RenameConflictError,
)
from app.service.project_sync import ProjectSyncCoordinator, operation_payload
from app.service.tier_export import (
    PROVENANCE_PROPERTY,
    TierReintegrationConflictError,
    reintegrate_tier_subset,
    research_extract_metadata,
)

project_lock_dep = Depends(project_write_lock)

router = APIRouter()

git_service = GitService()
sync_coordinator = ProjectSyncCoordinator(git_service)
logger = get_logger()

eaf_upload_files_dep = File(...)


async def _prepare_tier_scoped_uploads(
    files: list[UploadFile], project: Project
) -> list[UploadFile]:
    """Expand research extracts into safe full-file tier-scoped candidates."""
    prepared: list[UploadFile] = []
    project_files = Path(project.project_path) / "elan_files"
    marker = PROVENANCE_PROPERTY.encode()
    for upload in files:
        content = await upload.read()
        await upload.seek(0)
        if marker not in content:
            prepared.append(upload)
            continue

        metadata = research_extract_metadata(content)
        if metadata is None:
            prepared.append(upload)
            continue
        source_filename = metadata.get("source_filename")
        if (
            not isinstance(source_filename, str)
            or Path(source_filename).name != source_filename
            or not source_filename.lower().endswith(".eaf")
        ):
            raise HTTPException(
                status_code=400, detail="Research-copy source filename is invalid"
            )
        source = project_files / source_filename
        if not source.is_file():
            raise HTTPException(
                status_code=409,
                detail=f"The source file {source_filename} is no longer available.",
            )
        merged = reintegrate_tier_subset(source.read_bytes(), content)
        upload.filename = source_filename
        upload.file = BytesIO(merged)
        upload.size = len(merged)
        prepared.append(upload)
    return prepared


@router.get("/check", response_model=GitStatusResponse)
async def check_git(user: User = get_admin_dep) -> GitStatusResponse:
    """Check if Git is available on the system.

    Args:
        user: Authenticated admin user.

    Returns:
        GitStatusResponse: Git availability status, version, and any errors.

    Raises:
        HTTPException: 500 if Git check fails.

    """
    try:
        result = git_service.check_git_availability()
        return GitStatusResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/projects/create", response_model=ProjectCreateResponse)
async def create_project(
    project_data: ProjectCreateRequest,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Create a new ELAN project with Git repository.

    Args:
        project_data: Project creation request containing project name.
        user: Authenticated admin user.

    Returns:
        ProjectCreateResponse: Details of the created project including path and Git status.

    Raises:
        HTTPException: 400 if project already exists, 500 if creation fails.

    """
    try:
        result = await git_service.create_project(
            project_data.project_name,
            project_data.description,
            db,
            user.user_id,
            user.instance_id,
        )
        return ProjectCreateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        logger.exception("Unable to create project %r", project_data.project_name)
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/commit",
    response_model=CommitResponse,
    dependencies=[project_lock_dep],
)
async def commit_changes(
    project_name: str,
    commit_data: CommitRequest,
    user: User = get_admin_dep,
) -> CommitResponse:
    """Commit changes to a project.

    Args:
        project_name: Name of the project to commit changes to.
        commit_data: Commit request containing message and user information.

    Returns:
        CommitResponse: Details of the commit including hash and timestamp.

    Raises:
        HTTPException: 404 if project not found, 400 if no changes or invalid data, 500 if commit fails.

    """
    try:
        result = git_service.commit_changes(
            project_name, commit_data.commit_message, commit_data.user_name
        )
        return CommitResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_id}/upload",
    response_model=BatchFileUploadResponse,
    dependencies=[get_project_write_dep, project_lock_dep],
)
async def upload_elan_files(
    project_id: int,
    user_name: str = Form(...),
    files: list[UploadFile] = eaf_upload_files_dep,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> BatchFileUploadResponse:
    """Upload an ELAN file to a project.

    Args:
        project_id: Name of the project to upload file to.
        file: ELAN file (.eaf) to upload. File is validated for format and size.
        user_name: Name of the user uploading the file.

    Returns:
        FileUploadResponse: Details of the uploaded file including filename and timestamp.

    Raises:
        HTTPException: 404 if the project is absent, 422 if EAF validation
            fails, or 500 if upload processing fails.

    Note:
        File validation includes checking for .eaf extension, file size limits,
        valid ELAN XML structure, and filename compliance with the project's naming standard.

    """
    try:
        project = await db.get(Project, project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        files = await _prepare_tier_scoped_uploads(files, project)
        validated_batch = await validate_and_record_elan_files(
            files,
            db=db,
            instance_id=access.user.instance_id,
            project_id=project_id,
            requested_project_name=project.project_name,
            submitted_by=access.user.user_id,
        )
        result = await git_service.add_elan_files(
            project_id,
            validated_batch.files,
            db,
            access.user.user_id,
            user_name,
            protocol_validation={
                "outcome": validated_batch.protocol_outcome,
                "protocol_version_id": (
                    str(validated_batch.protocol_version_id)
                    if validated_batch.protocol_version_id
                    else None
                ),
                "rules_sha256": validated_batch.protocol_rules_sha256,
            },
        )
        return BatchFileUploadResponse(**result)
    except TierReintegrationConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tier_reintegration_conflict",
                "message": str(e),
                "filename": e.filename,
                "tiers": e.tiers,
            },
        ) from e
    except HTTPException:
        raise
    except (DuplicatePendingContributionError, ContributionAlreadyCurrentError) as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/projects/{project_name}/branches")
async def get_project_branches(project_name: str, user: User = get_admin_dep):
    """Get all branches for a project."""
    try:
        result = git_service.get_branches(project_name)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/checkout",
    response_model=ProjectCheckoutResponse,
    dependencies=[project_lock_dep],
)
async def checkout_project_branch(
    project_name: str,
    checkout_data: ProjectCheckoutRequest,
    user: User = get_admin_dep,
):
    """Switch to a different branch in the given project."""
    try:
        result = git_service.checkout_branch(project_name, checkout_data.branch_name)
        return ProjectCheckoutResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """List all project names for the current instance (admin only)."""
    projects = await git_service.list_projects(db, user.instance_id)
    return ProjectListResponse(projects=projects)


@router.get("/user-projects", response_model=ProjectListResponse)
async def list_user_projects(
    db: AsyncSession = get_db_dep,
    user: User = get_user_dep,
):
    """List project names that the current user has access to."""
    projects = await git_service.list_user_projects(db, user.user_id, user.instance_id)
    return ProjectListResponse(projects=projects)


@router.post("/projects/init-from-folder-upload", response_model=ProjectCreateResponse)
async def init_project_from_folder_upload(
    project_name: str = Form(...),
    description: str = Form(...),
    files: list[UploadFile] = eaf_upload_files_dep,
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
        result = await git_service.init_project_from_folder_upload(
            project_name,
            description,
            validated_batch.files,
            db,
            user.user_id,
            user.instance_id,
        )
        return ProjectCreateResponse(**result)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/projects/{project_name}/files")
async def get_project_files(
    project_name: str,
    include_media: bool = False,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
):
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
        result = await git_service.list_project_files(project_name, db, include_media)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/projects/{project_name}/synchronize/check",
    response_model=ProjectSyncCheckResponse,
    dependencies=[project_lock_dep],
)
async def synchronize_project_check(
    project_name: str,
    user: User = get_admin_dep,
):
    """Preview unmanaged server-side EAF changes without modifying the repository."""
    try:
        return git_service.synchronize_project_check(project_name)
    except Exception as e:
        logger.exception(
            "Failed to inspect server-side changes for project %r", project_name
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/projects/{project_name}", dependencies=[project_lock_dep])
async def delete_project(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Delete a project, its files, and all associated database artifacts."""
    try:
        await git_service.delete_project(project_name, db)
        return {"status": "success", "detail": f"Project '{project_name}' deleted."}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/edit",
    response_model=ProjectEditResponse,
    dependencies=[project_lock_dep],
)
async def edit_project(
    project_name: str,
    req: ProjectEditRequest,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    try:
        result = await git_service.edit_project(
            project_name, req.new_project_name, req.new_project_description, db
        )
        return ProjectEditResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except FileExistsError as e:
        raise HTTPException(status_code=409, detail="Project state conflict") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/synchronize",
    response_model=ProjectSyncExecutionResponse,
    dependencies=[project_lock_dep],
)
async def synchronize_project(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Synchronize the project's elan_files folder with the git repo and update the database.

    Only changed, added, or deleted files are processed.
    """
    try:
        operation = await sync_coordinator.execute(project_name, db, user.user_id)
        return {
            "project_name": project_name,
            "in_sync": operation.state == "completed",
            "files_status": operation.changes,
            "status": operation.state,
            "operation_id": str(operation.operation_id),
        }
    except (EafValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/projects/{project_name}/synchronize/operations",
    dependencies=[project_lock_dep],
)
async def list_synchronization_operations(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Return the durable administrator recovery history for one project."""
    try:
        operations = await sync_coordinator.list_for_project(project_name, db)
        return {"operations": [operation_payload(item) for item in operations]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


@router.post(
    "/projects/{project_name}/synchronize/operations/{operation_id}/recover",
    dependencies=[project_lock_dep],
)
async def recover_synchronization_operation(
    project_name: str,
    operation_id: uuid.UUID,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Reconcile PostgreSQL from a Git commit left by an interrupted operation."""
    try:
        operation = await sync_coordinator.recover(
            project_name, operation_id, db, user.user_id
        )
        return operation_payload(operation)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e


@router.post(
    "/projects/{project_name}/discard-local-changes", dependencies=[project_lock_dep]
)
async def discard_local_changes(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Preserve evidence, then reset the project folder to canonical Git state."""
    try:
        operation = await sync_coordinator.discard(project_name, db, user.user_id)
        return {
            "status": "success",
            "detail": "Server-side changes discarded",
            "operation_id": str(operation.operation_id),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/restore-from-backup", dependencies=[project_lock_dep]
)
async def restore_from_backup(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Restore the project folder from the most recent backup and update the database."""
    try:
        result = await git_service.restore_project_from_backup(
            project_name, db, user.user_id
        )
        return {"status": "success", "detail": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post("/projects/{project_name}/decline-backup", dependencies=[project_lock_dep])
async def decline_backup(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
):
    """Decline restoration of the most recent backup for the project, delete it and erase all related data from the database."""
    try:
        await git_service.decline_project_backup(db, project_name)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/projects/{project_name}/admin/pending-uploads",
    response_model=PendingUploadsResponse,
    dependencies=[get_project_read_dep],
)
async def get_pending_uploads(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
):
    """List contribution status for authorized project members."""
    try:
        result = await git_service.get_pending_uploads_with_status(project_name, db)
        return PendingUploadsResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


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


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/test",
    dependencies=[get_project_admin_dep],
)
async def test_pending_upload(
    project_name: str,
    branch_name: str,
    access: ProjectAccess = get_project_admin_dep,
):
    """Test whether a pending contribution merges cleanly without changing history."""
    try:
        return git_service.test_pending_upload(project_name, branch_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/eaf-review",
    response_model=EafReviewResponse,
    dependencies=[get_project_read_dep],
)
async def review_pending_eaf(
    project_name: str,
    branch_name: str,
    filename: str,
    access: ProjectAccess = get_project_read_dep,
) -> EafReviewResponse:
    """Return a read-only semantic comparison without mutating project state."""
    try:
        comparison = compare_repository_eaf(
            git_service.base_path, project_name, branch_name, filename
        )
        return EafReviewResponse(**comparison_payload(comparison))
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (EafReviewUnavailableError, EafValidationError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/merge",
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def merge_pending_upload(
    project_name: str,
    branch_name: str,
    request: PendingUploadMergeRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
):
    """Merge one reviewed contribution and mark its queue record resolved."""
    try:
        return await git_service.complete_pending_upload(
            project_name,
            branch_name,
            request.resolution_strategy,
            db,
            access.user.user_id,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/duplicate",
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def dismiss_duplicate_upload(
    project_name: str,
    upload_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
):
    """Remove a redundant pending branch while retaining provenance and audit history."""
    try:
        return await git_service.dismiss_duplicate_upload(
            project_name, upload_id, db, access.user.user_id
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/rename-file",
    response_model=FileRenameResponse,
    dependencies=[get_project_write_dep, project_lock_dep],
)
async def rename_file(
    project_name: str,
    elan_id: int = Form(...),
    new_filename: str = Form(...),
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> FileRenameResponse:
    """Rename a single file in the project."""
    try:
        result = await git_service.rename_file(
            project_name=project_name,
            elan_id=elan_id,
            new_filename=new_filename,
            db=db,
        )
        return result
    except RenameConflictError as e:
        # Return conflict info with 409 status code
        return FileRenameResponse(
            project_name=project_name,
            old_filename="",  # Will be filled by service if needed
            new_filename=new_filename,
            success=False,
            committed=False,
            commit_hash=None,
            renamed_at="",
            message=str(e),
            conflict_elan_id=e.conflict_elan_id,
            message_key=e.message_key,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/rename-files",
    response_model=BulkRenameResponse,
    dependencies=[get_project_write_dep, project_lock_dep],
)
async def rename_files(
    project_name: str,
    request: BulkRenameRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> BulkRenameResponse:
    """Rename multiple files in the project."""
    try:
        renames = [
            {"elan_id": rename.elan_id, "new_filename": rename.new_filename}
            for rename in request.renames
        ]
        result = await git_service.rename_files(
            project_name=project_name,
            renames=renames,
            db=db,
        )
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e
