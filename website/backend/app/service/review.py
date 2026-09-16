"""Transactional use cases for contribution review cases."""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.model.association import UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import ReviewCaseState, Status
from app.model.notification import Notification
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.protocol import ProtocolValidationIssue, ValidationRun
from app.model.review import ReviewCase, ReviewCaseView, ReviewComment, ReviewTask
from app.model.user import User
from app.schema.review import (
    ReviewCaseCreate,
    ReviewCaseResponse,
    ReviewCaseTransition,
    ReviewCommentCreate,
    ReviewCommentResponse,
    ReviewRevisionRequest,
    ReviewTaskResponse,
    ReviewTaskUpdate,
)
from app.service.git_command_runner import GitCommandRunner

ALLOWED_TRANSITIONS: dict[ReviewCaseState, frozenset[ReviewCaseState]] = {
    ReviewCaseState.OPEN: frozenset(
        {
            ReviewCaseState.CHANGES_REQUESTED,
            ReviewCaseState.RESOLVED,
            ReviewCaseState.CLOSED,
        }
    ),
    ReviewCaseState.CHANGES_REQUESTED: frozenset(
        {ReviewCaseState.RESUBMITTED, ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED}
    ),
    ReviewCaseState.RESUBMITTED: frozenset(
        {
            ReviewCaseState.CHANGES_REQUESTED,
            ReviewCaseState.RESOLVED,
            ReviewCaseState.CLOSED,
        }
    ),
    ReviewCaseState.RESOLVED: frozenset({ReviewCaseState.OPEN, ReviewCaseState.CLOSED}),
    ReviewCaseState.CLOSED: frozenset({ReviewCaseState.OPEN}),
}


def _queue_notification(
    db: AsyncSession,
    *,
    user_id: int | None,
    actor_id: int,
    title: str,
    message: str,
    project_id: int,
    case_id: uuid.UUID,
) -> None:
    """Queue an in-app notification inside the caller's transaction."""
    if user_id is None or user_id == actor_id:
        return
    db.add(
        Notification(
            user_id=user_id,
            title=title,
            message=message,
            action_url=(
                f"/contribution?project={project_id}&case={case_id}&view=reviews"
            ),
        )
    )


def _display_name(user: User | None) -> str:
    if user is None:
        return "Former member"
    return f"{user.first_name} {user.last_name}".strip() or user.username


def review_response(
    case: ReviewCase, viewer_id: int | None = None
) -> ReviewCaseResponse:
    view = next((item for item in case.views if item.user_id == viewer_id), None)
    return ReviewCaseResponse(
        case_id=case.case_id,
        project_id=case.project_id,
        upload_id=case.upload_id,
        resubmitted_upload_id=case.resubmitted_upload_id,
        resubmitted_upload_status=(
            case.resubmission.status.value if case.resubmission else None
        ),
        contributor_id=case.upload.submitted_by if case.upload else None,
        original_branch=case.upload.branch_name if case.upload else None,
        response_branch=case.resubmission.branch_name if case.resubmission else None,
        title=case.title,
        state=ReviewCaseState(case.state),
        filename=case.filename,
        tier_id=case.tier_id,
        annotation_id=case.annotation_id,
        current_text=case.current_text,
        suggested_text=case.suggested_text,
        validation_issue_id=case.validation_issue_id,
        start_ms=case.start_ms,
        end_ms=case.end_ms,
        created_by=case.created_by,
        creator_name=_display_name(case.creator),
        assigned_to=case.assigned_to,
        assignee_name=_display_name(case.assignee) if case.assignee else None,
        created_at=case.created_at,
        updated_at=case.updated_at,
        resolved_at=case.resolved_at,
        comments=[
            ReviewCommentResponse(
                comment_id=comment.comment_id,
                author_user_id=comment.author_user_id,
                author_name=_display_name(comment.author),
                parent_comment_id=comment.parent_comment_id,
                body=comment.body,
                created_at=comment.created_at,
            )
            for comment in case.comments
        ],
        tasks=[
            ReviewTaskResponse(
                task_id=task.task_id,
                filename=task.filename,
                instruction=task.instruction,
                tier_id=task.tier_id,
                annotation_id=task.annotation_id,
                start_ms=task.start_ms,
                end_ms=task.end_ms,
                current_text=task.current_text,
                suggested_text=task.suggested_text,
                status=task.status,
                created_at=task.created_at,
            )
            for task in case.tasks
        ],
        unread=viewer_id is not None
        and (view is None or view.viewed_at < case.updated_at),
    )


def _case_options() -> tuple[ExecutableOption, ...]:
    return (
        selectinload(ReviewCase.creator),
        selectinload(ReviewCase.assignee),
        selectinload(ReviewCase.comments).selectinload(ReviewComment.author),
        selectinload(ReviewCase.tasks),
        selectinload(ReviewCase.views),
        selectinload(ReviewCase.upload),
        selectinload(ReviewCase.resubmission),
    )


async def get_case(db: AsyncSession, project_id: int, case_id: uuid.UUID) -> ReviewCase:
    case = await db.scalar(
        select(ReviewCase)
        .where(ReviewCase.project_id == project_id, ReviewCase.case_id == case_id)
        .options(*_case_options())
        .execution_options(populate_existing=True)
    )
    if case is None:
        raise FileNotFoundError("Review case not found")
    return case


async def list_cases(
    db: AsyncSession,
    project_id: int,
    upload_id: int | None = None,
    viewer_id: int | None = None,
) -> list[ReviewCaseResponse]:
    query = select(ReviewCase).where(ReviewCase.project_id == project_id)
    if upload_id is not None:
        query = query.where(ReviewCase.upload_id == upload_id)
    cases = (
        await db.scalars(
            query.options(*_case_options()).order_by(ReviewCase.updated_at.desc())
        )
    ).all()
    return [review_response(case, viewer_id) for case in cases]


async def create_case(
    db: AsyncSession, project_id: int, actor_id: int, request: ReviewCaseCreate
) -> ReviewCaseResponse:
    upload: PendingUpload | None = None
    if request.upload_id is not None:
        upload = await db.scalar(
            select(PendingUpload).where(
                PendingUpload.upload_id == request.upload_id,
                PendingUpload.project_id == project_id,
            )
        )
        if upload is None:
            raise ValueError("Submission does not belong to this project")
    if request.validation_issue_id is not None:
        issue = await db.scalar(
            select(ProtocolValidationIssue)
            .join(ValidationRun)
            .join(EafRevision)
            .join(ElanFile)
            .where(
                ProtocolValidationIssue.validation_issue_id
                == request.validation_issue_id,
                ElanFile.project_id == project_id,
            )
        )
        if issue is None:
            raise ValueError("Compliance finding does not belong to this project")
    case = ReviewCase(
        project_id=project_id,
        upload_id=request.upload_id,
        state=(
            ReviewCaseState.CHANGES_REQUESTED.value
            if request.request_changes
            else ReviewCaseState.OPEN.value
        ),
        title=request.title.strip(),
        filename=request.filename,
        tier_id=request.tier_id,
        annotation_id=request.annotation_id,
        current_text=(request.current_text or "").strip() or None,
        suggested_text=(request.suggested_text or "").strip() or None,
        validation_issue_id=request.validation_issue_id,
        start_ms=request.start_ms,
        end_ms=request.end_ms,
        created_by=actor_id,
        # The researcher opening a review owns its follow-up by default. This
        # can be reassigned, but active work never starts without a clear lead.
        assigned_to=actor_id,
    )
    db.add(case)
    await db.flush()
    for task in request.tasks:
        db.add(ReviewTask(case_id=case.case_id, **task.model_dump()))
    if request.initial_comment:
        db.add(
            ReviewComment(
                case_id=case.case_id,
                author_user_id=actor_id,
                body=request.initial_comment.strip(),
            )
        )
    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=project_id,
            action="review_case.created",
            resource_type="review_case",
            resource_id=str(case.case_id),
            details={
                "upload_id": request.upload_id,
                "initial_state": case.state,
            },
        )
    )
    if request.request_changes:
        upload_submitter = upload.submitted_by if upload is not None else None
        _queue_notification(
            db,
            user_id=upload_submitter,
            actor_id=actor_id,
            title="Corrections requested",
            message=case.title,
            project_id=project_id,
            case_id=case.case_id,
        )
    await db.commit()
    return review_response(await get_case(db, project_id, case.case_id))


async def mark_case_viewed(
    db: AsyncSession, project_id: int, case_id: uuid.UUID, user_id: int
) -> ReviewCaseResponse:
    await get_case(db, project_id, case_id)
    view = await db.get(ReviewCaseView, {"case_id": case_id, "user_id": user_id})
    if view is None:
        db.add(
            ReviewCaseView(
                case_id=case_id, user_id=user_id, viewed_at=datetime.now(UTC)
            )
        )
    else:
        view.viewed_at = datetime.now(UTC)
    await db.commit()
    return review_response(await get_case(db, project_id, case_id), user_id)


async def _resolve_approved_correction(
    db: AsyncSession, case: ReviewCase, actor_id: int
) -> None:
    """Close a satisfied correction and classify a content-identical response."""
    now = datetime.now(UTC)
    case.state = ReviewCaseState.RESOLVED.value
    case.resolved_at = now
    case.updated_at = now

    outcome = "correction_approved"
    resubmission = case.resubmission
    if resubmission is not None and resubmission.branch_name:
        project = await db.get(Project, case.project_id)
        if project is None:
            raise FileNotFoundError("Project not found")
        runner = GitCommandRunner(Path(project.project_path), maintain_backup=False)
        if runner.get_tree_hash(resubmission.branch_name) == runner.get_tree_hash():
            resubmission.status = Status.NO_CHANGES
            resubmission.resolved_at = now
            resubmission.resolved_by = actor_id
            outcome = "no_project_changes"
            db.add(
                AuditEvent(
                    actor_user_id=actor_id,
                    project_id=case.project_id,
                    action="contribution.no_project_changes",
                    resource_type="pending_upload",
                    resource_id=str(resubmission.upload_id),
                    details={
                        "review_case_id": str(case.case_id),
                        "reason": "correction_matches_shared_project",
                    },
                )
            )

    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=case.project_id,
            action="review_case.correction_approved",
            resource_type="review_case",
            resource_id=str(case.case_id),
            details={"outcome": outcome},
        )
    )
    contributor_id = case.upload.submitted_by if case.upload else None
    _queue_notification(
        db,
        user_id=contributor_id,
        actor_id=actor_id,
        title="Correction approved",
        message=(
            "The correction was confirmed; no project content changed."
            if outcome == "no_project_changes"
            else "The correction review was completed."
        ),
        project_id=case.project_id,
        case_id=case.case_id,
    )


async def update_review_task(
    db: AsyncSession,
    project_id: int,
    case_id: uuid.UUID,
    task_id: uuid.UUID,
    actor_id: int,
    request: ReviewTaskUpdate,
    *,
    can_manage: bool,
) -> ReviewCaseResponse:
    case = await get_case(db, project_id, case_id)
    task = next((item for item in case.tasks if item.task_id == task_id), None)
    if task is None:
        raise FileNotFoundError("Review task not found")
    contributor_id = case.upload.submitted_by if case.upload else None
    if request.status == "addressed" and actor_id != contributor_id:
        raise PermissionError(
            "Only the researcher who submitted the contribution may mark work done"
        )
    if (
        request.status == "addressed"
        and ReviewCaseState(case.state) != ReviewCaseState.CHANGES_REQUESTED
    ):
        raise ValueError("Work can only be marked done while corrections are requested")
    if request.status in {"accepted", "reopened"} and not can_manage:
        raise PermissionError("Only a project administrator may review correction work")
    if (
        request.status in {"accepted", "reopened"}
        and ReviewCaseState(case.state) != ReviewCaseState.RESUBMITTED
    ):
        raise ValueError(
            "Correction work can only be reviewed after a corrected revision is submitted"
        )
    task.status = request.status
    case.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=project_id,
            action="review_task.updated",
            resource_type="review_task",
            resource_id=str(task_id),
            details={"status": request.status},
        )
    )
    if request.status == "accepted" and all(
        item.status == "accepted" for item in case.tasks
    ):
        await _resolve_approved_correction(db, case, actor_id)
    await db.commit()
    return review_response(await get_case(db, project_id, case_id), actor_id)


async def request_review_revision(
    db: AsyncSession,
    project_id: int,
    case_id: uuid.UUID,
    actor_id: int,
    request: ReviewRevisionRequest,
) -> ReviewCaseResponse:
    """Atomically return selected edits and their required feedback."""
    case = await get_case(db, project_id, case_id)
    if ReviewCaseState(case.state) != ReviewCaseState.RESUBMITTED:
        raise ValueError("Another revision can only be requested after resubmission")
    selected_ids = set(request.task_ids)
    selected = [task for task in case.tasks if task.task_id in selected_ids]
    if len(selected) != len(selected_ids):
        raise ValueError("One or more requested edits do not belong to this review")
    for task in selected:
        task.status = "reopened"
    case.state = ReviewCaseState.CHANGES_REQUESTED.value
    case.updated_at = datetime.now(UTC)
    db.add(
        ReviewComment(
            case_id=case.case_id,
            author_user_id=actor_id,
            body=request.feedback.strip(),
        )
    )
    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=project_id,
            action="review_case.revision_requested",
            resource_type="review_case",
            resource_id=str(case_id),
            details={"task_ids": [str(task_id) for task_id in request.task_ids]},
        )
    )
    contributor_id = case.upload.submitted_by if case.upload else None
    _queue_notification(
        db,
        user_id=contributor_id,
        actor_id=actor_id,
        title="Another revision requested",
        message=case.title,
        project_id=project_id,
        case_id=case_id,
    )
    await db.commit()
    return review_response(await get_case(db, project_id, case_id), actor_id)


async def add_comment(
    db: AsyncSession,
    project_id: int,
    case_id: uuid.UUID,
    actor_id: int,
    request: ReviewCommentCreate,
) -> ReviewCaseResponse:
    case = await get_case(db, project_id, case_id)
    if ReviewCaseState(case.state) in {
        ReviewCaseState.RESOLVED,
        ReviewCaseState.CLOSED,
    }:
        raise ValueError("Closed review discussions cannot be changed")
    if request.parent_comment_id is not None and not any(
        item.comment_id == request.parent_comment_id for item in case.comments
    ):
        raise ValueError("Parent comment does not belong to this review case")
    comment = ReviewComment(
        case_id=case_id,
        author_user_id=actor_id,
        parent_comment_id=request.parent_comment_id,
        body=request.body.strip(),
    )
    db.add(comment)
    await db.flush()
    case.updated_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=project_id,
            action="review_comment.created",
            resource_type="review_case",
            resource_id=str(case_id),
            details={"comment_id": str(comment.comment_id)},
        )
    )
    discussion_recipient = (
        case.assigned_to
        if case.assigned_to is not None and case.assigned_to != actor_id
        else case.created_by
    )
    _queue_notification(
        db,
        user_id=discussion_recipient,
        actor_id=actor_id,
        title="New review comment",
        message=case.title,
        project_id=project_id,
        case_id=case_id,
    )
    await db.commit()
    return review_response(await get_case(db, project_id, case_id))


async def transition_case(
    db: AsyncSession,
    project_id: int,
    case_id: uuid.UUID,
    actor_id: int,
    request: ReviewCaseTransition,
) -> ReviewCaseResponse:
    case = await get_case(db, project_id, case_id)
    previous = ReviewCaseState(case.state)
    previous_assignee = case.assigned_to
    if request.state != previous and request.state not in ALLOWED_TRANSITIONS[previous]:
        raise ValueError(f"Cannot move a review from {previous} to {request.state}")
    if "assigned_to" in request.model_fields_set and request.assigned_to is not None:
        project = await db.get(Project, project_id)
        membership = await db.scalar(
            select(UserToProject).where(
                UserToProject.project_id == project_id,
                UserToProject.user_id == request.assigned_to,
            )
        )
        assignee = await db.get(User, request.assigned_to)
        is_institution_admin = (
            project is not None
            and assignee is not None
            and assignee.instance_id == project.instance_id
            and assignee.role.value == "admin"
        )
        if assignee is None or (membership is None and not is_institution_admin):
            raise ValueError("Assignee must be a member of this project")
    if (
        "assigned_to" in request.model_fields_set
        and request.assigned_to is None
        and request.state not in {ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED}
    ):
        raise ValueError("An active review must have a review lead")
    if request.state == ReviewCaseState.RESUBMITTED:
        if request.resubmitted_upload_id is None:
            raise ValueError("A resubmitted review must reference the new submission")
        resubmission = await db.scalar(
            select(PendingUpload).where(
                PendingUpload.upload_id == request.resubmitted_upload_id,
                PendingUpload.project_id == project_id,
            )
        )
        if resubmission is None:
            raise ValueError("Resubmission does not belong to this project")
        previous_upload_id = case.resubmitted_upload_id or case.upload_id
        if (
            previous_upload_id is not None
            and previous_upload_id != resubmission.upload_id
        ):
            previous_upload = await db.get(PendingUpload, previous_upload_id)
            if previous_upload is not None:
                previous_upload.superseded_by_upload_id = resubmission.upload_id
        # Linking a corrected upload is the contributor's commit-like signal.
        # The reviewer must still decide whether each requested edit is
        # acceptable, but requiring a separate "mark done" click adds no state.
        for task in case.tasks:
            if task.status in {"requested", "reopened"}:
                task.status = "addressed"
    if (
        request.state == ReviewCaseState.RESOLVED
        and previous == ReviewCaseState.RESUBMITTED
        and all(task.status == "accepted" for task in case.tasks)
    ):
        await _resolve_approved_correction(db, case, actor_id)
    else:
        case.state = request.state.value
    if "assigned_to" in request.model_fields_set:
        case.assigned_to = request.assigned_to
    elif case.assigned_to is None and request.state not in {
        ReviewCaseState.RESOLVED,
        ReviewCaseState.CLOSED,
    }:
        # Bring historical unassigned cases into the current invariant when a
        # reviewer next acts on them.
        case.assigned_to = actor_id
    if "resubmitted_upload_id" in request.model_fields_set:
        case.resubmitted_upload_id = request.resubmitted_upload_id
    case.updated_at = datetime.now(UTC)
    case.resolved_at = (
        datetime.now(UTC)
        if request.state in {ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED}
        else None
    )
    db.add(
        AuditEvent(
            actor_user_id=actor_id,
            project_id=project_id,
            action="review_case.transitioned",
            resource_type="review_case",
            resource_id=str(case_id),
            details={"from": previous.value, "to": request.state.value},
        )
    )
    if case.assigned_to != previous_assignee:
        _queue_notification(
            db,
            user_id=case.assigned_to,
            actor_id=actor_id,
            title="Review assigned to you",
            message=case.title,
            project_id=project_id,
            case_id=case_id,
        )
    if request.state == ReviewCaseState.CHANGES_REQUESTED:
        _queue_notification(
            db,
            user_id=case.created_by,
            actor_id=actor_id,
            title="Changes requested",
            message=case.title,
            project_id=project_id,
            case_id=case_id,
        )
    if request.state == ReviewCaseState.RESUBMITTED:
        _queue_notification(
            db,
            user_id=case.created_by,
            actor_id=actor_id,
            title="Corrected contribution submitted",
            message=f"{case.title} · contribution #{case.resubmitted_upload_id}",
            project_id=project_id,
            case_id=case_id,
        )
    await db.commit()
    return review_response(await get_case(db, project_id, case_id))
