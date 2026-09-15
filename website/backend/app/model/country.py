from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .city import City


class Country(Base):
    """Country model representing countries in the system."""

    __tablename__ = "COUNTRY"

    country_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    country_code: Mapped[str] = mapped_column(
        String(2), nullable=False, unique=True, index=True
    )
    country_name: Mapped[str] = mapped_column(
        String(100), nullable=False, unique=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    cities: Mapped[list["City"]] = relationship("City", back_populates="country")

    def __repr__(self) -> str:
        """Return a string representation of the Country."""
        return f"<Country(country_id={self.country_id}, country_code='{self.country_code}', country_name='{self.country_name}')>"
