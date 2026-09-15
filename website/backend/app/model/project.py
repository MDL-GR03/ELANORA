import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    Text,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .elan_file import ElanFile
    from .instance import Instance
    from .invitation import Invitation
    from .pending_upload import PendingUpload
    from .project_revision import ProjectRevision


class Project(Base):
    """Project model representing annotation projects."""

    __tablename__ = "PROJECT"
    __table_args__ = (
        ForeignKeyConstraint(
            ["current_revision_id", "project_id"],
            ["PROJECT_REVISION.revision_id", "PROJECT_REVISION.project_id"],
            name="fk_project_current_revision",
            ondelete="RESTRICT",
            use_alter=True,
        ),
        CheckConstraint(
            "data_classification IS NULL OR data_classification IN "
            "('public', 'internal', 'confidential', 'sensitive_personal')",
            name="ck_project_data_classification",
        ),
        # Personal data needs a recorded lawful basis or consent reference.
        CheckConstraint(
            "data_classification IS DISTINCT FROM 'sensitive_personal' "
            "OR btrim(coalesce(legal_basis, '')) <> ''",
            name="ck_project_sensitive_legal_basis",
        ),
        CheckConstraint(
            "retention_days IS NULL OR retention_days >= 30",
            name="ck_project_retention_days",
        ),
        CheckConstraint(
            "NOT legal_hold OR btrim(coalesce(legal_hold_reason, '')) <> ''",
            name="ck_project_legal_hold_reason",
        ),
    )

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
    current_revision_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        nullable=True,
        index=True,
    )
    auto_accept_new_files: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    # Data governance. An unclassified project has no classification yet; a
    # project without a retention period is kept until someone decides.
    data_classification: Mapped[str | None] = mapped_column(String(30), nullable=True)
    legal_basis: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Days a deleted project's content is kept before it may be purged.
    retention_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    legal_hold: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    legal_hold_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Set once a deleted project's research content has been destroyed.
    content_purged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    governance_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    governance_updated_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
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
    current_revision: Mapped["ProjectRevision | None"] = relationship(
        "ProjectRevision", foreign_keys=[current_revision_id], post_update=True
    )

    def __repr__(self) -> str:
        """Return a string representation of the Project."""
        return f"<Project(project_id={self.project_id}, project_name='{self.project_name}')>"
