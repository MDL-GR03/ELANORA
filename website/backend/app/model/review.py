"""Durable, revision-oriented contribution review records."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.model.enums import ReviewCaseState

if TYPE_CHECKING:
    from app.model.pending_upload import PendingUpload
    from app.model.project import Project
    from app.model.user import User


class ReviewCase(Base):
    """One actionable discussion anchored to a submitted contribution."""

    __tablename__ = "REVIEW_CASE"
    __table_args__ = (
        CheckConstraint(
            "state IN ('open','changes_requested','resubmitted','resolved','closed')",
            name="ck_review_case_state",
        ),
        CheckConstraint(
            "start_ms IS NULL OR start_ms >= 0", name="ck_review_case_start_ms"
        ),
        CheckConstraint(
            "end_ms IS NULL OR end_ms >= start_ms", name="ck_review_case_interval"
        ),
        Index("ix_review_case_project_state", "project_id", "state"),
    )

    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("PENDING_UPLOAD.upload_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    resubmitted_upload_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("PENDING_UPLOAD.upload_id", ondelete="RESTRICT"),
        nullable=True,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(
        String(32), nullable=False, default=ReviewCaseState.OPEN.value
    )
    filename: Mapped[str | None] = mapped_column(String(512), nullable=True)
    tier_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    annotation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    current_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    validation_issue_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("VALIDATION_ISSUE.validation_issue_id", ondelete="SET NULL"),
        nullable=True,
    )
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    assigned_to: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship("Project")
    upload: Mapped["PendingUpload | None"] = relationship(
        "PendingUpload", foreign_keys=[upload_id]
    )
    resubmission: Mapped["PendingUpload | None"] = relationship(
        "PendingUpload", foreign_keys=[resubmitted_upload_id]
    )
    creator: Mapped["User | None"] = relationship("User", foreign_keys=[created_by])
    assignee: Mapped["User | None"] = relationship("User", foreign_keys=[assigned_to])
    comments: Mapped[list["ReviewComment"]] = relationship(
        "ReviewComment",
        back_populates="review_case",
        cascade="all, delete-orphan",
        order_by="ReviewComment.created_at",
    )
    tasks: Mapped[list["ReviewTask"]] = relationship(
        "ReviewTask",
        back_populates="review_case",
        cascade="all, delete-orphan",
        order_by="ReviewTask.created_at",
    )
    views: Mapped[list["ReviewCaseView"]] = relationship(
        "ReviewCaseView", back_populates="review_case", cascade="all, delete-orphan"
    )


class ReviewTask(Base):
    """One independently reviewable file-level correction request."""

    __tablename__ = "REVIEW_TASK"
    __table_args__ = (
        CheckConstraint(
            "status IN ('requested','addressed','accepted','reopened')",
            name="ck_review_task_status",
        ),
        CheckConstraint(
            "start_ms IS NULL OR start_ms >= 0", name="ck_review_task_start"
        ),
        CheckConstraint(
            "end_ms IS NULL OR end_ms >= start_ms", name="ck_review_task_interval"
        ),
    )

    task_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("REVIEW_CASE.case_id", ondelete="CASCADE"),
        index=True,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    instruction: Mapped[str] = mapped_column(Text, nullable=False)
    tier_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    annotation_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="requested")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    review_case: Mapped["ReviewCase"] = relationship(
        "ReviewCase", back_populates="tasks"
    )


class ReviewCaseView(Base):
    """Last time one project member inspected a review case."""

    __tablename__ = "REVIEW_CASE_VIEW"
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("REVIEW_CASE.case_id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="CASCADE"), primary_key=True
    )
    viewed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_case: Mapped["ReviewCase"] = relationship(
        "ReviewCase", back_populates="views"
    )


class ReviewComment(Base):
    """An append-only message in a contribution review case."""

    __tablename__ = "REVIEW_COMMENT"

    comment_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("REVIEW_CASE.case_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    author_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    parent_comment_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("REVIEW_COMMENT.comment_id", ondelete="RESTRICT"),
        nullable=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    review_case: Mapped["ReviewCase"] = relationship(
        "ReviewCase", back_populates="comments"
    )
    author: Mapped["User | None"] = relationship("User")
    parent: Mapped["ReviewComment | None"] = relationship(
        "ReviewComment", remote_side=[comment_id]
    )
