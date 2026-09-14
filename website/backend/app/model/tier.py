from typing import TYPE_CHECKING, Optional

from sqlalchemy import JSON, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .annotation import Annotation


class Tier(Base):
    """Tier model representing annotation tiers."""

    __tablename__ = "TIER"

    tier_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tier_name: Mapped[str] = mapped_column(String)
    linguistic_type_ref: Mapped[str] = mapped_column(String(255), nullable=False)
    eaf_attributes: Mapped[dict[str, str]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ELAN_FILE.elan_id", ondelete="CASCADE"), nullable=False
    )
    parent_tier_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("TIER.tier_id", ondelete="CASCADE"), nullable=True
    )

    # Relationships
    parent_tier: Mapped[Optional["Tier"]] = relationship(
        "Tier", remote_side="Tier.tier_id", back_populates="child_tiers"
    )
    child_tiers: Mapped[list["Tier"]] = relationship(
        "Tier", back_populates="parent_tier"
    )
    annotations: Mapped[list["Annotation"]] = relationship(
        "Annotation", back_populates="tier", overlaps="elan_file"
    )

    __table_args__ = (
        UniqueConstraint("elan_id", "tier_name", name="uq_tier_elan_name"),
        UniqueConstraint("tier_id", "elan_id", name="uq_tier_identity_elan"),
    )

    def __repr__(self) -> str:
        """Return a string representation of the Tier."""
        return f"<Tier(tier_id='{self.tier_id}', tier_name='{self.tier_name}')>"
