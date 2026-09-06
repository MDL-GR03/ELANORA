import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .elan_file import ElanFile
    from .instance import Instance
    from .invitation import Invitation
    from .pending_upload import PendingUpload


class Project(Base):
    """Project model representing annotation projects."""

    __tablename__ = "PROJECT"

    project_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    project_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("INSTANCE.instance_id", ondelete="CASCADE"), nullable=False
    )
    project_path: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    protocol_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROTOCOL_VERSION.protocol_version_id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    auto_accept_new_files: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    # Relationships - use string references
    elan_files: Mapped[list["ElanFile"]] = relationship(
        "ElanFile", back_populates="project", cascade="all, delete-orphan"
    )
    pending_uploads: Mapped[list["PendingUpload"]] = relationship(
        "PendingUpload", back_populates="project", cascade="all, delete-orphan"
    )
    instance: Mapped["Instance"] = relationship("Instance", back_populates="projects")
    invitations: Mapped[list["Invitation"]] = relationship(
        "Invitation", back_populates="project"
    )

    def __repr__(self) -> str:
        """Return a string representation of the Project."""
        return f"<Project(project_id={self.project_id}, project_name='{self.project_name}')>"
