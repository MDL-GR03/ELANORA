"""Transactional use cases for contribution review cases."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.base import ExecutableOption

from app.model.association import UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import ReviewCaseState
from app.model.notification import Notification
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.protocol import ProtocolValidationIssue, ValidationRun
from app.model.review import ReviewCase, ReviewComment
from app.model.user import User
from app.schema.review import (
    ReviewCaseCreate,
    ReviewCaseResponse,
    ReviewCaseTransition,
    ReviewCommentCreate,
    ReviewCommentResponse,
)

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


def review_response(case: ReviewCase) -> ReviewCaseResponse:
    return ReviewCaseResponse(
        case_id=case.case_id,
        project_id=case.project_id,
        upload_id=case.upload_id,
        resubmitted_upload_id=case.resubmitted_upload_id,
        title=case.title,
        state=ReviewCaseState(case.state),
        filename=case.filename,
        tier_id=case.tier_id,
        annotation_id=case.annotation_id,
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
    )


def _case_options() -> tuple[ExecutableOption, ...]:
    return (
        selectinload(ReviewCase.creator),
        selectinload(ReviewCase.assignee),
        selectinload(ReviewCase.comments).selectinload(ReviewComment.author),
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
    db: AsyncSession, project_id: int, upload_id: int | None = None
) -> list[ReviewCaseResponse]:
    query = select(ReviewCase).where(ReviewCase.project_id == project_id)
    if upload_id is not None:
        query = query.where(ReviewCase.upload_id == upload_id)
    cases = (
        await db.scalars(
            query.options(*_case_options()).order_by(ReviewCase.updated_at.desc())
        )
    ).all()
    return [review_response(case) for case in cases]


async def create_case(
    db: AsyncSession, project_id: int, actor_id: int, request: ReviewCaseCreate
) -> ReviewCaseResponse:
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
        upload_submitter = (
            upload.submitted_by if request.upload_id is not None else None
        )
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


async def add_comment(
    db: AsyncSession,
    project_id: int,
    case_id: uuid.UUID,
    actor_id: int,
    request: ReviewCommentCreate,
) -> ReviewCaseResponse:
    case = await get_case(db, project_id, case_id)
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
        and request.state
        not in {ReviewCaseState.RESOLVED, ReviewCaseState.CLOSED}
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
    await db.commit()
    return review_response(await get_case(db, project_id, case_id))
