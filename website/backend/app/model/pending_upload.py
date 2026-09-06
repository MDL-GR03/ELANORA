from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

from .enums import Severity, Status, Type

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class PendingUpload(Base):
    """PendingUpload model representing detected uploads in projects."""

    __tablename__ = "PENDING_UPLOAD"

    upload_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    upload_type: Mapped[Type] = mapped_column(SQLEnum(Type), nullable=False)
    upload_description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[Severity] = mapped_column(
        SQLEnum(Severity), nullable=False, default=Severity.MEDIUM
    )
    status: Mapped[Status] = mapped_column(
        SQLEnum(Status), nullable=False, default=Status.PENDING_ADMIN_APPROVAL
    )
    detected_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.current_timestamp()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id"), nullable=True
    )
    submitted_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("USER.user_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    branch_name: Mapped[str | None] = mapped_column(String, nullable=True)
    base_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    accepted_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    git_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )

    # Relationships
    project: Mapped["Project"] = relationship(
        "Project", back_populates="pending_uploads"
    )
    resolver: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[resolved_by], back_populates="resolved_uploads"
    )
    submitter: Mapped[Optional["User"]] = relationship(
        "User", foreign_keys=[submitted_by], back_populates="submitted_uploads"
    )

    def __repr__(self) -> str:
        """Return a string representation of the PendingUpload."""
        return f"<Upload(upload_id='{self.upload_id}', upload_type='{self.upload_type}', status='{self.status}', detected_at='{self.detected_at}', project_id='{self.project_id}', branch_name='{self.branch_name}')>"
