from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .user import User


class NotificationPreference(Base):
    """NotificationPreference model representing user notification preferences."""

    __tablename__ = "NOTIFICATION_PREFERENCE"

    preference_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("USER.user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        unique=True,
    )
    email_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User", back_populates="notification_preference"
    )

    def __repr__(self) -> str:
        """Return a string representation of the notification preference."""
        return f"<NotificationPreference(id={self.preference_id}, user_id={self.user_id}, email_enabled={self.email_enabled})>"
