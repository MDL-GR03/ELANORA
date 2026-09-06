"""Immutable records of EAF payloads rejected at the ingestion boundary."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    JSON,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EafIngestionAttempt(Base):
    """A rejected source payload retained for diagnosis and recovery."""

    __tablename__ = "EAF_INGESTION_ATTEMPT"
    __table_args__ = (
        CheckConstraint("file_size >= 0", name="ck_eaf_ingestion_file_size"),
        CheckConstraint("length(sha256) = 64", name="ck_eaf_ingestion_sha256"),
        CheckConstraint("status = 'rejected'", name="ck_eaf_ingestion_status"),
    )

    attempt_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("INSTANCE.instance_id", ondelete="RESTRICT"), nullable=False
    )
    project_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="SET NULL"), nullable=True
    )
    submitted_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    requested_project_name: Mapped[str] = mapped_column(String(100), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_xml: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="rejected")
    validation_issues: Mapped[list[dict[str, str]]] = mapped_column(
        JSON, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
