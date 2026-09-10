"""Durable publication requests for reviewed researcher contributions."""

import uuid
from datetime import UTC, datetime

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
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ContributionChangeSet(Base):
    """Recoverable coordination state for publishing one pending contribution."""

    __tablename__ = "CONTRIBUTION_CHANGE_SET"
    __table_args__ = (
        CheckConstraint(
            "state IN ('queued','running','completed','review_needed','failed')",
            name="ck_contribution_change_set_state",
        ),
        CheckConstraint(
            "resolution_strategy IN ('auto','accept_incoming','accept_current')",
            name="ck_contribution_change_set_resolution_strategy",
        ),
        Index("ix_contribution_change_set_state", "state", "created_at"),
        Index("uq_contribution_change_set_upload_id", "upload_id", unique=True),
    )

    change_set_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    upload_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PENDING_UPLOAD.upload_id", ondelete="RESTRICT"),
        nullable=False,
    )
    requested_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    branch_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resolution_strategy: Mapped[str] = mapped_column(String(32), nullable=False)
    expected_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    resulting_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    state: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
