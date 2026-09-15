from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .city import City
    from .user import User


class Address(Base):
    """Address model representing addresses in the system."""

    __tablename__ = "ADDRESS"

    address_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    street_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    street_name: Mapped[str] = mapped_column(String(100), nullable=False)
    city_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("CITY.city_id"), nullable=False, index=True
    )
    postal_code: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    address_line_2: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=func.now(), onupdate=func.now()
    )

    # Relationships
    city: Mapped["City"] = relationship("City", back_populates="addresses")
    users: Mapped[list["User"]] = relationship("User", back_populates="address")

    def __repr__(self) -> str:
        """Return a string representation of the Address."""
        return f"<Address(address_id={self.address_id}, street_name='{self.street_name}', city_id={self.city_id})>"
