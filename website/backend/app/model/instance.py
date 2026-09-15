import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .project import Project
    from .user import User


class Instance(Base):
    """The single institution profile owned by this installation."""

    __tablename__ = "INSTANCE"
    __table_args__ = (
        CheckConstraint(
            "primary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_instance_primary_color_hex",
        ),
        CheckConstraint(
            "secondary_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_instance_secondary_color_hex",
        ),
        CheckConstraint(
            "accent_color ~ '^#[0-9A-Fa-f]{6}$'",
            name="ck_instance_accent_color_hex",
        ),
    )

    instance_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    installation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        nullable=False,
        unique=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    singleton_key: Mapped[int] = mapped_column(
        Integer,
        CheckConstraint("singleton_key = 1", name="ck_instance_singleton_key"),
        nullable=False,
        unique=True,
        default=1,
        server_default=text("1"),
    )
    instance_name: Mapped[str] = mapped_column(String(100), nullable=False)
    institution_name: Mapped[str] = mapped_column(String(100), nullable=False)
    contact_email: Mapped[str] = mapped_column(String(100), nullable=False)
    domain: Mapped[str] = mapped_column(String(100), nullable=False)
    timezone: Mapped[str] = mapped_column(String(50), nullable=False)
    default_language: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en"
    )
    primary_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#2563eb", server_default="#2563eb"
    )
    secondary_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#0f766e", server_default="#0f766e"
    )
    accent_color: Mapped[str] = mapped_column(
        String(7), nullable=False, default="#d97706", server_default="#d97706"
    )
    logo_asset_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid,
        ForeignKey("INSTANCE_ASSET.asset_id", use_alter=True, ondelete="SET NULL"),
        nullable=True,
    )
    max_file_size_mb: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), nullable=False, default=100.00
    )
    max_users: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    projects: Mapped[list["Project"]] = relationship(
        "Project", back_populates="instance"
    )
    users: Mapped[list["User"]] = relationship("User", back_populates="instance")

    def __repr__(self) -> str:
        """Return a string representation of the Instance."""
        return f"<Instance(instance_id={self.instance_id}, instance_name='{self.instance_name}')>"

    @property
    def logo_url(self) -> str | None:
        return "/api/v1/instance/logo" if self.logo_asset_id is not None else None
