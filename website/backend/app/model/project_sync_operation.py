"""Durable saga records for administrator-imported server changes."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
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


class ProjectSyncOperation(Base):
    """Recoverable coordination state across PostgreSQL, Git, and staging storage."""

    __tablename__ = "PROJECT_SYNC_OPERATION"
    __table_args__ = (
        CheckConstraint(
            "state IN ('preparing','prepared','committing','completed','discarded','failed','recovery_required')",
            name="ck_project_sync_operation_state",
        ),
        Index("ix_project_sync_operation_project_id", "project_id"),
        Index("ix_project_sync_operation_state", "state"),
    )

    operation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PROJECT.project_id", ondelete="CASCADE"),
        nullable=False,
    )
    initiated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    state: Mapped[str] = mapped_column(String(32), nullable=False)
    changes: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    evidence_manifest: Mapped[list[dict[str, object]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    staging_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    starting_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resulting_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
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
    evidence_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
