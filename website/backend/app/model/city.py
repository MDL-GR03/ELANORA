from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .address import Address
    from .country import Country


class City(Base):
    """City model representing cities in the system."""

    __tablename__ = "CITY"

    city_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    city_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    country_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("COUNTRY.country_id"), nullable=False
    )
    region_state: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    country: Mapped["Country"] = relationship("Country", back_populates="cities")
    addresses: Mapped[list["Address"]] = relationship("Address", back_populates="city")

    # Indexes
    __table_args__ = (Index("idx_country_city", "country_id", "city_name"),)

    def __repr__(self) -> str:
        """Return a string representation of the City."""
        return f"<City(city_id={self.city_id}, city_name='{self.city_name}', country_id={self.country_id})>"
