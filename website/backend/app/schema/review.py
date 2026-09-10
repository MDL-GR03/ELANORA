"""API contracts for contribution review cases and discussions."""

import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.model.enums import ReviewCaseState
from app.schema.common.base import CustomBaseModel


class ReviewTaskCreate(CustomBaseModel):
    filename: str = Field(min_length=1, max_length=512)
    instruction: str = Field(min_length=1, max_length=10_000)
    tier_id: str | None = Field(default=None, max_length=255)
    annotation_id: str | None = Field(default=None, max_length=255)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    current_text: str | None = Field(default=None, max_length=10_000)
    suggested_text: str | None = Field(default=None, max_length=10_000)

    @model_validator(mode="after")
    def valid_interval(self) -> "ReviewTaskCreate":
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms < self.start_ms
        ):
            raise ValueError("end_ms must not precede start_ms")
        return self


class ReviewTaskResponse(ReviewTaskCreate):
    task_id: uuid.UUID
    status: str
    created_at: datetime


class ReviewTaskUpdate(CustomBaseModel):
    status: str = Field(pattern="^(requested|addressed|accepted|reopened)$")


class ReviewRevisionRequest(CustomBaseModel):
    task_ids: list[uuid.UUID] = Field(min_length=1, max_length=100)
    feedback: str = Field(min_length=1, max_length=10_000)


class ReviewCaseCreate(CustomBaseModel):
    upload_id: int | None = None
    request_changes: bool = False
    title: str = Field(min_length=1, max_length=200)
    filename: str | None = Field(default=None, max_length=512)
    tier_id: str | None = Field(default=None, max_length=255)
    annotation_id: str | None = Field(default=None, max_length=255)
    current_text: str | None = Field(default=None, max_length=10_000)
    suggested_text: str | None = Field(default=None, max_length=10_000)
    validation_issue_id: uuid.UUID | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    initial_comment: str | None = Field(default=None, min_length=1, max_length=10_000)
    tasks: list[ReviewTaskCreate] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def valid_interval(self) -> "ReviewCaseCreate":
        if self.upload_id is None and self.validation_issue_id is None:
            raise ValueError("a submission or compliance finding is required")
        if self.request_changes and not self.tasks and not self.filename:
            raise ValueError(
                "a correction request must identify at least one file to change"
            )
        if (
            self.start_ms is not None
            and self.end_ms is not None
            and self.end_ms < self.start_ms
        ):
            raise ValueError("end_ms must not precede start_ms")
        return self


class ReviewCommentCreate(CustomBaseModel):
    body: str = Field(min_length=1, max_length=10_000)
    parent_comment_id: uuid.UUID | None = None


class ReviewCaseTransition(CustomBaseModel):
    state: ReviewCaseState
    assigned_to: int | None = None
    resubmitted_upload_id: int | None = None


class ReviewCaseResubmit(CustomBaseModel):
    """A contributor's explicit link to a corrected submission."""

    upload_id: int


class ReviewCommentResponse(CustomBaseModel):
    comment_id: uuid.UUID
    author_user_id: int | None
    author_name: str
    parent_comment_id: uuid.UUID | None
    body: str
    created_at: datetime


class ReviewCaseResponse(CustomBaseModel):
    case_id: uuid.UUID
    project_id: int
    upload_id: int | None
    resubmitted_upload_id: int | None
    resubmitted_upload_status: str | None
    contributor_id: int | None
    original_branch: str | None
    response_branch: str | None
    title: str
    state: ReviewCaseState
    filename: str | None
    tier_id: str | None
    annotation_id: str | None
    current_text: str | None
    suggested_text: str | None
    validation_issue_id: uuid.UUID | None
    start_ms: int | None
    end_ms: int | None
    created_by: int | None
    creator_name: str
    assigned_to: int | None
    assignee_name: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    comments: list[ReviewCommentResponse]
    tasks: list[ReviewTaskResponse]
    unread: bool = False
