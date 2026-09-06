import uuid
from datetime import UTC, datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class InstanceAsset(Base):
    """Immutable metadata for an institution-owned visual asset."""

    __tablename__ = "INSTANCE_ASSET"
    __table_args__ = (
        CheckConstraint("kind = 'logo'", name="ck_instance_asset_kind"),
        CheckConstraint(
            "byte_size > 0 AND width > 0 AND height > 0",
            name="ck_instance_asset_dimensions",
        ),
        CheckConstraint("length(sha256) = 64", name="ck_instance_asset_sha256"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    instance_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("INSTANCE.instance_id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    byte_size: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    width: Mapped[int] = mapped_column(Integer, nullable=False)
    height: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
