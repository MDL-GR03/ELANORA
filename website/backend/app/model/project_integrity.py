"""Durable health state for accepted project data."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .project import Project
    from .project_revision import ProjectRevision


class ProjectIntegrityStatus(Base):
    """Latest integrity scan state and incident lifecycle for one project."""

    __tablename__ = "PROJECT_INTEGRITY_STATUS"

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PROJECT.project_id", ondelete="CASCADE"),
        primary_key=True,
    )
    revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROJECT_REVISION.revision_id", ondelete="RESTRICT"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    details: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    first_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    project: Mapped["Project"] = relationship("Project")
    revision: Mapped["ProjectRevision | None"] = relationship("ProjectRevision")
