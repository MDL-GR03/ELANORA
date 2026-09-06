"""Immutable source revisions for ELAN documents."""

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.model.elan_file import ElanFile
    from app.model.user import User


class EafRevision(Base):
    """One validated, content-addressed revision of an EAF file."""

    __tablename__ = "EAF_REVISION"
    __table_args__ = (
        UniqueConstraint("elan_id", "revision_number", name="uq_eaf_revision_number"),
        UniqueConstraint("elan_id", "sha256", name="uq_eaf_revision_content"),
        CheckConstraint("revision_number > 0", name="ck_eaf_revision_positive"),
        CheckConstraint("length(sha256) = 64", name="ck_eaf_revision_sha256"),
    )

    revision_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ELAN_FILE.elan_id", ondelete="CASCADE"), nullable=False
    )
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    raw_xml: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    object_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    parser_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    elan_file: Mapped["ElanFile"] = relationship("ElanFile")
    creator: Mapped["User | None"] = relationship("User")
