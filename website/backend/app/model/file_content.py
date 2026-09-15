from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .elan_file import ElanFile
    from .user import User


class FileContent(Base):
    """FileContent model representing unique file content with deduplication."""

    __tablename__ = "FILE_CONTENT"

    content_id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("USER.user_id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="file_contents")
    elan_files: Mapped[list["ElanFile"]] = relationship(
        "ElanFile", back_populates="file_content", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Return a string representation of the FileContent."""
        return f"<FileContent(content_id={self.content_id}, filename='{self.filename}', content_hash='{self.content_hash[:8]}...')>"
