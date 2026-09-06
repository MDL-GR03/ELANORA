from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .annotation_value import AnnotationValue
    from .elan_file import ElanFile
    from .tier import Tier


class Annotation(Base):
    """Annotation model representing individual annotations."""

    __tablename__ = "ANNOTATION"

    annotation_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ELAN_FILE.elan_id", ondelete="CASCADE"), primary_key=True
    )

    value_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ANNOTATION_VALUE.value_id", ondelete="CASCADE"),
        nullable=False,
    )
    annotation_kind: Mapped[str] = mapped_column(String(16), nullable=False)
    annotation_ref: Mapped[str | None] = mapped_column(String(50), nullable=True)
    previous_annotation: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cv_entry_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(255), nullable=True)
    start_time: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    end_time: Mapped[Decimal | None] = mapped_column(Numeric(14, 3), nullable=True)
    tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("TIER.tier_id"), nullable=False
    )

    # Relationships
    tier: Mapped["Tier"] = relationship("Tier", back_populates="annotations")
    annotation_value: Mapped["AnnotationValue"] = relationship("AnnotationValue")
    elan_file: Mapped["ElanFile"] = relationship("ElanFile")

    def __repr__(self) -> str:
        """Return a string representation of the Annotation."""
        return f"<Annotation(annotation_id='{self.annotation_id}', value_id={self.value_id}, start_time={self.start_time}, end_time={self.end_time}, tier_id={self.tier_id})>"
