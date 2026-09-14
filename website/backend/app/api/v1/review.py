"""Project-scoped contribution review API."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
    get_project_write_dep,
)
from app.dependency.project_lock import project_write_lock
from app.model.enums import ProjectPermission, ReviewCaseState
from app.model.pending_upload import PendingUpload
from app.schema.review import (
    ReviewCaseCreate,
    ReviewCaseResponse,
    ReviewCaseResubmit,
    ReviewCaseTransition,
    ReviewCommentCreate,
    ReviewRevisionRequest,
    ReviewTaskUpdate,
)
from app.service.review import (
    add_comment,
    create_case,
    get_case,
    list_cases,
    mark_case_viewed,
    request_review_revision,
    transition_case,
    update_review_task,
)

router = APIRouter()
project_lock_dep = Depends(project_write_lock)
REVIEW_NOT_FOUND = "Review case or task not found"
INVALID_REVIEW_OPERATION = "Invalid review operation"
REVIEW_ACTION_FORBIDDEN = "Review action not permitted"


@router.get("/projects/{project_id}/cases", response_model=list[ReviewCaseResponse])
async def get_review_cases(
    project_id: int,
    upload_id: int | None = None,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> list[ReviewCaseResponse]:
    """List review cases visible to a project member."""
    return await list_cases(
        db, access.project.project_id, upload_id, access.user.user_id
    )


@router.post(
    "/projects/{project_id}/cases",
    response_model=ReviewCaseResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[project_lock_dep],
)
async def post_review_case(
    project_id: int,
    request: ReviewCaseCreate,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> ReviewCaseResponse:
    """Open an actionable case against a submitted contribution."""
    try:
        return await create_case(
            db, access.project.project_id, access.user.user_id, request
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/comments",
    response_model=ReviewCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_review_comment(
    project_id: int,
    case_id: uuid.UUID,
    request: ReviewCommentCreate,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> ReviewCaseResponse:
    """Append a contributor comment; existing discussion is never edited."""
    try:
        return await add_comment(
            db,
            access.project.project_id,
            case_id,
            access.user.user_id,
            request,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc


@router.patch(
    "/projects/{project_id}/cases/{case_id}",
    response_model=ReviewCaseResponse,
    dependencies=[project_lock_dep],
)
async def patch_review_case(
    project_id: int,
    case_id: uuid.UUID,
    request: ReviewCaseTransition,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ReviewCaseResponse:
    """Assign or transition a review case as a project administrator."""
    try:
        return await transition_case(
            db,
            access.project.project_id,
            case_id,
            access.user.user_id,
            request,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/resubmission",
    response_model=ReviewCaseResponse,
    dependencies=[project_lock_dep],
)
async def post_review_resubmission(
    project_id: int,
    case_id: uuid.UUID,
    request: ReviewCaseResubmit,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> ReviewCaseResponse:
    """Link a contributor's corrected upload to a requested-change case."""
    try:
        review_case = await get_case(db, access.project.project_id, case_id)
        if ReviewCaseState(review_case.state) != ReviewCaseState.CHANGES_REQUESTED:
            raise ValueError("Only a requested-change case can be resubmitted")
        submission = await db.scalar(
            select(PendingUpload).where(
                PendingUpload.upload_id == request.upload_id,
                PendingUpload.project_id == access.project.project_id,
            )
        )
        if submission is None:
            raise ValueError("Resubmission does not belong to this project")
        if access.permission not in {
            ProjectPermission.ADMIN,
            ProjectPermission.OWNER,
        } and (
            submission.submitted_by != access.user.user_id
            or review_case.upload is None
            or review_case.upload.submitted_by != access.user.user_id
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the submitting researcher may link this contribution",
            )
        return await transition_case(
            db,
            access.project.project_id,
            case_id,
            access.user.user_id,
            ReviewCaseTransition(
                state=ReviewCaseState.RESUBMITTED,
                resubmitted_upload_id=request.upload_id,
            ),
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/view",
    response_model=ReviewCaseResponse,
)
async def post_review_case_view(
    project_id: int,
    case_id: uuid.UUID,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> ReviewCaseResponse:
    """Persist that the current member inspected the latest case activity."""
    try:
        return await mark_case_viewed(
            db, access.project.project_id, case_id, access.user.user_id
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc


@router.patch(
    "/projects/{project_id}/cases/{case_id}/tasks/{task_id}",
    response_model=ReviewCaseResponse,
)
async def patch_review_task(
    project_id: int,
    case_id: uuid.UUID,
    task_id: uuid.UUID,
    request: ReviewTaskUpdate,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> ReviewCaseResponse:
    """Update one file task without resolving unrelated requested files."""
    try:
        return await update_review_task(
            db,
            access.project.project_id,
            case_id,
            task_id,
            access.user.user_id,
            request,
            can_manage=access.permission
            in {ProjectPermission.ADMIN, ProjectPermission.OWNER},
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc
    except PermissionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=REVIEW_ACTION_FORBIDDEN
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc


@router.post(
    "/projects/{project_id}/cases/{case_id}/revision-request",
    response_model=ReviewCaseResponse,
    dependencies=[project_lock_dep],
)
async def post_review_revision_request(
    project_id: int,
    case_id: uuid.UUID,
    request: ReviewRevisionRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ReviewCaseResponse:
    """Return selected edits with mandatory feedback in one transaction."""
    try:
        return await request_review_revision(
            db,
            access.project.project_id,
            case_id,
            access.user.user_id,
            request,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=REVIEW_NOT_FOUND) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=INVALID_REVIEW_OPERATION) from exc
