"""API contracts for contribution review cases and discussions."""

import uuid
from datetime import datetime

from pydantic import Field, model_validator

from app.model.enums import ReviewCaseState
from app.schema.common.base import CustomBaseModel


class ReviewCaseCreate(CustomBaseModel):
    upload_id: int | None = None
    request_changes: bool = False
    title: str = Field(min_length=1, max_length=200)
    filename: str | None = Field(default=None, max_length=512)
    tier_id: str | None = Field(default=None, max_length=255)
    annotation_id: str | None = Field(default=None, max_length=255)
    validation_issue_id: uuid.UUID | None = None
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    initial_comment: str | None = Field(default=None, min_length=1, max_length=10_000)

    @model_validator(mode="after")
    def valid_interval(self) -> "ReviewCaseCreate":
        if self.upload_id is None and self.validation_issue_id is None:
            raise ValueError("a submission or compliance finding is required")
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
    title: str
    state: ReviewCaseState
    filename: str | None
    tier_id: str | None
    annotation_id: str | None
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
