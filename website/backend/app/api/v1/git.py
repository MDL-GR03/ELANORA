import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.exceptions import RenameConflictError
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
from app.model.enums import ReviewCaseState
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.research_topic import (
    ProjectBaselineTier,
    ResearchTopic,
    ResearchTopicTier,
)
from app.model.review import ReviewCase
from app.model.user import User
from app.schema.requests.git import (
    BulkRenameRequest,
    ContributionPolicyRequest,
    ContributionResearchTopicRequest,
    PendingUploadDeclineRequest,
    PendingUploadMergeRequest,
    ProjectCheckoutRequest,
    ProjectCreateRequest,
    ProjectEditRequest,
    ProjectRevisionRecoveryRequest,
    ProjectVersionPreviewRequest,
    ProjectVersionRestoreRequest,
)
from app.schema.responses.git import (
    AcceptedProjectHistoryResponse,
    BatchFileUploadResponse,
    BulkRenameResponse,
    EafReviewResponse,
    FileRenameResponse,
    GitStatusResponse,
    PendingUploadsResponse,
    ProjectCheckoutResponse,
    ProjectCreateResponse,
    ProjectEditResponse,
    ProjectFilesResponse,
    ProjectFilesWithMediaResponse,
    ProjectListResponse,
    ProjectRevisionHealthResponse,
    ProjectRevisionRecoveryResponse,
    ProjectSyncCheckResponse,
    ProjectSyncExecutionResponse,
    ProjectVersionPreviewResponse,
    ProjectVersionRestoreResponse,
)
from app.service.contribution_change_set import ContributionChangeSetCoordinator
from app.service.contribution_intake import (
    ContributionAlreadyCurrentError,
    DuplicatePendingContributionError,
)
from app.service.eaf_review import (
    EafReviewUnavailableError,
    compare_repository_eaf,
    comparison_payload,
)
from app.service.git import GitService
from app.service.project_lifecycle import ProjectNameUnavailableError
from app.service.project_sync import ProjectSyncCoordinator, operation_payload
from app.service.research_topics import (
    SimilarResearchTopicError,
    require_distinct_topic_name,
)
from app.service.tier_export import (
    PROVENANCE_PROPERTY,
    ProtectedContextModifiedError,
    TierReintegrationConflictError,
    reintegrate_tier_subset,
    research_extract_metadata,
)
from app.service.upload_naming_compliance import FilenameNotCompliantError

project_lock_dep = Depends(project_write_lock)

router = APIRouter()
PROJECT_RESOURCE_NOT_FOUND = "Project resource not found"
PROJECT_STATE_CONFLICT = "Project state conflict"
INVALID_PROJECT_STATE = "Invalid project state"

git_service = GitService()
contribution_change_sets = ContributionChangeSetCoordinator(git_service)

# Deleted projects stay restorable by name, so their names remain reserved.
PROJECT_NAME_UNAVAILABLE = (
    "This name is already used by another project, including a deleted project "
    "that can still be restored. Choose a different name."
)
sync_coordinator = ProjectSyncCoordinator(git_service)
logger = get_logger()

eaf_upload_files_dep = File(...)
correction_case_id_dep = Form(default=None)


def _string_list(value: object) -> list[str]:
    """Return only string members from untrusted persisted JSON arrays."""
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


async def _prepare_tier_scoped_uploads(
    files: list[UploadFile],
    project: Project,
    db: AsyncSession,
    *,
    declared_topic_id: int | None,
    proposed_topic_name: str | None,
    contribution_summary: str | None,
) -> tuple[list[UploadFile], dict[str, object]]:
    """Expand research extracts into safe full-file tier-scoped candidates."""
    prepared: list[UploadFile] = []
    scoped_files: list[dict[str, object]] = []
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
        selected_tiers = metadata.get("selected_tiers", [])
        scoped_files.append(
            {
                "filename": source_filename,
                "topic_id": metadata.get("research_topic_id"),
                "topic_name": metadata.get("research_topic"),
                "selected_tiers": selected_tiers,
                "automatically_included_tiers": metadata.get(
                    "included_parent_tiers", []
                ),
                "baseline_context_tiers": metadata.get("context_tiers", []),
                "editable_baseline_tiers": metadata.get("editable_baseline_tiers", []),
            }
        )
        upload.filename = source_filename
        upload.file = BytesIO(merged)
        upload.size = len(merged)
        prepared.append(upload)

    topic = None
    topic_match = "selected_existing" if declared_topic_id is not None else None
    if declared_topic_id is not None:
        topic = await db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.topic_id == declared_topic_id,
                ResearchTopic.project_id == project.project_id,
            )
        )
        if topic is None:
            raise HTTPException(status_code=422, detail="Research topic not found.")
    embedded_topic_ids = {
        item["topic_id"]
        for item in scoped_files
        if isinstance(item.get("topic_id"), int)
    }
    if declared_topic_id is not None and embedded_topic_ids - {declared_topic_id}:
        raise HTTPException(
            status_code=409,
            detail="The selected research topic does not match the downloaded research copy.",
        )
    if topic is None and len(embedded_topic_ids) == 1:
        embedded_topic_id = next(iter(embedded_topic_ids))
        topic = await db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.topic_id == embedded_topic_id,
                ResearchTopic.project_id == project.project_id,
            )
        )
    if len(embedded_topic_ids) > 1:
        raise HTTPException(
            status_code=422,
            detail="Upload research copies from one research topic at a time.",
        )

    proposed_name = (proposed_topic_name or "").strip()
    if topic is None and not scoped_files and proposed_name:
        project_topics = list(
            (
                await db.scalars(
                    select(ResearchTopic).where(
                        ResearchTopic.project_id == project.project_id
                    )
                )
            ).all()
        )
        try:
            require_distinct_topic_name(proposed_name, project_topics)
        except SimilarResearchTopicError as exc:
            suggested = exc.topic
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "similar_research_topic",
                    "message": f'Did you mean the existing topic "{suggested.name}"?',
                    "suggested_topic_id": getattr(suggested, "topic_id", None),
                    "suggested_topic_name": suggested.name,
                },
            ) from exc

    topic_tiers = []
    if topic is not None:
        topic_tiers = list(
            (
                await db.scalars(
                    select(ResearchTopicTier.tier_name).where(
                        ResearchTopicTier.topic_id == topic.topic_id
                    )
                )
            ).all()
        )
    baseline_tiers = list(
        (
            await db.scalars(
                select(ProjectBaselineTier.tier_name).where(
                    ProjectBaselineTier.project_id == project.project_id
                )
            )
        ).all()
    )
    scoped_tiers_set: set[str] = set()
    for item in scoped_files:
        selected_tiers = item.get("selected_tiers")
        if isinstance(selected_tiers, list):
            scoped_tiers_set.update(
                tier for tier in selected_tiers if isinstance(tier, str)
            )
    scoped_tiers = sorted(scoped_tiers_set)
    editable_baseline_tiers = sorted(
        {
            tier
            for item in scoped_files
            for tier in _string_list(item.get("editable_baseline_tiers"))
        }
    )
    subject = topic.name if topic else None
    if subject is None and scoped_files:
        embedded_names = {
            str(item["topic_name"]) for item in scoped_files if item.get("topic_name")
        }
        subject = next(iter(embedded_names)) if len(embedded_names) == 1 else None
    return prepared, {
        "summary": (contribution_summary or "").strip(),
        "declared_topic_id": topic.topic_id if topic else None,
        "declared_topic_name": subject,
        "declared_tiers": sorted(set(topic_tiers)) or scoped_tiers,
        "baseline_tiers": sorted(set(baseline_tiers)),
        "declared_baseline_correction_tiers": editable_baseline_tiers,
        "source": "research_copy" if scoped_files else "researcher_declaration",
        "topic_match": topic_match,
        "proposed_topic_name": proposed_name if topic is None else None,
        "topic_review_status": (
            "proposed" if proposed_name and topic is None else "verified"
        ),
        "scoped_files": scoped_files,
    }


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
) -> ProjectCreateResponse:
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
        logger.error(
            "Unable to create a project; error_type=%s", safe_exception_type(e)
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_id}/upload",
    response_model=BatchFileUploadResponse,
    dependencies=[get_project_write_dep, project_lock_dep],
)
async def upload_elan_files(  # noqa: PLR0913, PLR0917
    project_id: int,
    user_name: str = Form(...),
    correction_case_id: uuid.UUID | None = correction_case_id_dep,
    research_topic_id: int | None = Form(default=None),
    proposed_topic_name: str | None = Form(default=None, max_length=100),
    contribution_summary: str = Form(min_length=3, max_length=1000),
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
        allow_current_tree = False
        if correction_case_id is not None:
            review_case = await db.get(ReviewCase, correction_case_id)
            if review_case is None or review_case.project_id != project_id:
                raise HTTPException(
                    status_code=404, detail="Correction request not found"
                )
            original_upload = (
                await db.get(PendingUpload, review_case.upload_id)
                if review_case.upload_id is not None
                else None
            )
            if (
                ReviewCaseState(review_case.state) != ReviewCaseState.CHANGES_REQUESTED
                or original_upload is None
                or original_upload.submitted_by != access.user.user_id
            ):
                raise HTTPException(
                    status_code=409,
                    detail="This correction request cannot accept a new response.",
                )
            allow_current_tree = True
        files, research_context = await _prepare_tier_scoped_uploads(
            files,
            project,
            db,
            declared_topic_id=research_topic_id,
            proposed_topic_name=proposed_topic_name,
            contribution_summary=contribution_summary,
        )
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
            research_context=research_context,
            allow_current_tree=allow_current_tree,
        )
        return BatchFileUploadResponse(**result)
    except ProtectedContextModifiedError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "protected_baseline_modified",
                "message": "Protected baseline tiers were modified",
                "filename": e.filename,
                "tiers": e.tiers,
            },
        ) from e
    except TierReintegrationConflictError as e:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "tier_reintegration_conflict",
                "message": "Submitted tiers conflict with the accepted file",
                "filename": e.filename,
                "tiers": e.tiers,
            },
        ) from e
    except FilenameNotCompliantError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "code": "filename_not_compliant",
                "message": (
                    "This project requires uploaded filenames to follow its "
                    "naming standard. Rename the file and upload it again."
                ),
                "filename": e.filename,
                "pattern": e.pattern,
            },
        ) from e
    except HTTPException:
        raise
    except (DuplicatePendingContributionError, ContributionAlreadyCurrentError) as e:
        raise HTTPException(
            status_code=409, detail="Contribution state conflict"
        ) from e
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail="Invalid project operation") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.get("/projects/{project_name}/branches")
async def get_project_branches(
    project_name: str, user: User = get_admin_dep
) -> dict[str, Any]:
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
) -> ProjectCheckoutResponse:
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
) -> ProjectListResponse:
    """List all project names for the current instance (admin only)."""
    projects = await git_service.list_projects(db, user.instance_id)
    return ProjectListResponse(projects=projects)


@router.get("/user-projects", response_model=ProjectListResponse)
async def list_user_projects(
    db: AsyncSession = get_db_dep,
    user: User = get_user_dep,
) -> ProjectListResponse:
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
        result = await git_service.list_project_files(project_name, db, include_media)
        response_type = (
            ProjectFilesWithMediaResponse if include_media else ProjectFilesResponse
        )
        return response_type(**result)
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
) -> ProjectSyncCheckResponse:
    """Preview unmanaged server-side EAF changes without modifying the repository."""
    try:
        return ProjectSyncCheckResponse(
            **git_service.synchronize_project_check(project_name)
        )
    except Exception as e:
        logger.error(
            "Failed to inspect server-side project changes; error_type=%s",
            safe_exception_type(e),
        )
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.delete("/projects/{project_name}", dependencies=[project_lock_dep])
async def delete_project(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
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
) -> ProjectEditResponse:
    try:
        result = await git_service.edit_project(
            project_name, req.new_project_name, req.new_project_description, db
        )
        return ProjectEditResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except ProjectNameUnavailableError as e:
        raise HTTPException(status_code=409, detail=PROJECT_NAME_UNAVAILABLE) from e
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
) -> ProjectSyncExecutionResponse:
    """Synchronize the project's elan_files folder with the git repo and update the database.

    Only changed, added, or deleted files are processed.
    """
    try:
        operation = await sync_coordinator.execute(project_name, db, user.user_id)
        return ProjectSyncExecutionResponse(
            project_name=project_name,
            in_sync=operation.state == "completed",
            files_status=operation.changes,
            status=operation.state,
            operation_id=str(operation.operation_id),
        )
    except (EafValidationError, ValueError) as e:
        raise HTTPException(status_code=422, detail=INVALID_PROJECT_STATE) from e
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
) -> dict[str, list[dict[str, Any]]]:
    """Return the durable administrator recovery history for one project."""
    try:
        operations = await sync_coordinator.list_for_project(project_name, db)
        return {"operations": [operation_payload(item) for item in operations]}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e


@router.post(
    "/projects/{project_name}/synchronize/operations/{operation_id}/recover",
    dependencies=[project_lock_dep],
)
async def recover_synchronization_operation(
    project_name: str,
    operation_id: uuid.UUID,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, Any]:
    """Reconcile PostgreSQL from a Git commit left by an interrupted operation."""
    try:
        operation = await sync_coordinator.recover(
            project_name, operation_id, db, user.user_id
        )
        return operation_payload(operation)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from e


@router.post(
    "/projects/{project_name}/discard-local-changes", dependencies=[project_lock_dep]
)
async def discard_local_changes(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
    """Preserve evidence, then reset the project folder to canonical Git state."""
    try:
        operation = await sync_coordinator.discard(project_name, db, user.user_id)
        return {
            "status": "success",
            "detail": "Server-side changes discarded",
            "operation_id": str(operation.operation_id),
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/restore-from-backup", dependencies=[project_lock_dep]
)
async def restore_from_backup(
    project_name: str,
    db: AsyncSession = get_db_dep,
    user: User = get_admin_dep,
) -> dict[str, str]:
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
) -> None:
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
) -> PendingUploadsResponse:
    """List contribution status for authorized project members."""
    try:
        result = await git_service.get_pending_uploads_with_status(project_name, db)
        return PendingUploadsResponse(**result)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail="Project or file not found") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


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
        result = await git_service.get_accepted_project_history(project_name, db)
        return AcceptedProjectHistoryResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc


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
        result = await git_service.get_current_revision_health(project_name, db)
        return ProjectRevisionHealthResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc


@router.post(
    "/projects/{project_name}/accepted-history/recover",
    response_model=ProjectRevisionRecoveryResponse,
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def recover_current_project_revision(
    project_name: str,
    request: ProjectRevisionRecoveryRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectRevisionRecoveryResponse:
    """Repair the current accepted EAF state from its immutable ledger manifest."""
    try:
        result = await git_service.recover_current_revision_from_manifest(
            project_name,
            request.revision_id,
            db,
            access.user.user_id,
            reason=request.reason,
            confirmation=request.confirmation,
        )
        return ProjectRevisionRecoveryResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, RuntimeError, EafValidationError) as exc:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from exc


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
        result = await git_service.preview_project_version_restore(
            project_name, request.target_commit, db
        )
        return ProjectVersionPreviewResponse(**result)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, EafValidationError) as exc:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from exc


@router.post(
    "/projects/{project_name}/accepted-history/restore",
    response_model=ProjectVersionRestoreResponse,
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def restore_project_version(
    project_name: str,
    request: ProjectVersionRestoreRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectVersionRestoreResponse:
    """Restore an older tree as a new, fully audited canonical version."""
    try:
        result = await git_service.restore_project_version(
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
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc
    except (ValueError, EafValidationError) as exc:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from exc


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
) -> dict[str, Any]:
    """Test whether a pending contribution merges cleanly without changing history."""
    try:
        return git_service.test_pending_upload(project_name, branch_name)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
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
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc
    except (EafReviewUnavailableError, EafValidationError) as exc:
        raise HTTPException(
            status_code=422, detail="EAF review is unavailable"
        ) from exc


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
) -> dict[str, Any]:
    """Durably request and execute publication of one reviewed contribution."""
    try:
        change_set = await contribution_change_sets.request(
            db,
            project_name=project_name,
            branch_name=branch_name,
            resolution_strategy=request.resolution_strategy,
            requested_by=access.user.user_id,
        )
        return await contribution_change_sets.execute(db, change_set.change_set_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/decline",
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def decline_pending_upload(
    project_name: str,
    upload_id: int,
    request: PendingUploadDeclineRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Decline a contribution while retaining its provenance and review history."""
    try:
        return await git_service.decline_pending_upload(
            project_name, upload_id, request.reason, db, access.user.user_id
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@router.put(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/research-topic",
    dependencies=[get_project_admin_dep],
)
async def set_contribution_research_topic(
    project_name: str,
    upload_id: int,
    request: ContributionResearchTopicRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Assign or create the curated topic used to classify a contribution."""
    try:
        return await git_service.set_contribution_research_topic(
            project_name,
            upload_id,
            request.topic_id,
            request.new_topic_name,
            db,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from exc


@router.delete(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/duplicate",
    dependencies=[get_project_admin_dep, project_lock_dep],
)
async def dismiss_duplicate_upload(
    project_name: str,
    upload_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Remove a redundant pending branch while retaining provenance and audit history."""
    try:
        return await git_service.dismiss_duplicate_upload(
            project_name, upload_id, db, access.user.user_id
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise HTTPException(status_code=409, detail=PROJECT_STATE_CONFLICT) from e
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
            message="A file with the target name already exists",
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
