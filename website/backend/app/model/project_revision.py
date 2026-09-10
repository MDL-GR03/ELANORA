"""Immutable ledger entries for accepted project states."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ProjectRevision(Base):
    """One durable, ordered record of a published project state."""

    __tablename__ = "PROJECT_REVISION"
    __table_args__ = (
        UniqueConstraint("project_id", "ordinal", name="uq_project_revision_ordinal"),
        UniqueConstraint("project_id", "git_commit", name="uq_project_revision_commit"),
        CheckConstraint("ordinal > 0", name="ck_project_revision_ordinal_positive"),
        CheckConstraint(
            "source_type IN ('contribution', 'restoration', 'migration')",
            name="ck_project_revision_source_type",
        ),
        CheckConstraint(
            "manifest_sha256 IS NULL OR length(manifest_sha256) = 64",
            name="ck_project_revision_manifest_sha256",
        ),
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PROJECT.project_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    git_commit: Mapped[str] = mapped_column(String(64), nullable=False)
    parent_git_commit: Mapped[str | None] = mapped_column(String(64), nullable=True)
    manifest_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False)
    contribution_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("PENDING_UPLOAD.upload_id", ondelete="SET NULL"),
        nullable=True,
    )
    actor_user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class ProjectRevisionEaf(Base):
    """One immutable filename-to-EAF-revision entry in a project manifest."""

    __tablename__ = "PROJECT_REVISION_EAF"
    __table_args__ = (
        CheckConstraint("length(sha256) = 64", name="ck_project_revision_eaf_sha256"),
    )

    project_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("PROJECT_REVISION.revision_id", ondelete="CASCADE"),
        primary_key=True,
    )
    filename: Mapped[str] = mapped_column(String(255), primary_key=True)
    eaf_revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("EAF_REVISION.revision_id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
