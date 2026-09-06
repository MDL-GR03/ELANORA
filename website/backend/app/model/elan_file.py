from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base
from app.utils.file_processing import make_path_absolute_from_projects

if TYPE_CHECKING:
    from .association import ElanFileToMedia
    from .file_content import FileContent
    from .project import Project


class ElanFile(Base):
    """ElanFile model representing ELAN annotation files with normalized content."""

    __tablename__ = "ELAN_FILE"

    elan_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("FILE_CONTENT.content_id", ondelete="CASCADE"),
        nullable=False,
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    last_modified: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # Add unique constraint for content within a project (same file can't be in project twice)
    __table_args__ = (
        UniqueConstraint("content_id", "project_id", name="uq_content_project"),
    )

    # Relationships
    file_content: Mapped["FileContent"] = relationship(
        "FileContent", back_populates="elan_files"
    )
    project: Mapped["Project"] = relationship("Project", back_populates="elan_files")
    media_links: Mapped[list["ElanFileToMedia"]] = relationship(
        "ElanFileToMedia", back_populates="elan_file", cascade="all, delete-orphan"
    )

    @property
    def file_size(self) -> int:
        """Get the file size from the associated file content."""
        return self.file_content.file_size

    @property
    def user_id(self) -> int | None:
        """Get the user ID from the associated file content."""
        return self.file_content.user_id

    @property
    def absolute_file_path(self) -> str:
        """Get the absolute file path by combining elanora_projects base with relative path."""
        return make_path_absolute_from_projects(self.file_path)

    def __repr__(self) -> str:
        """Return a string representation of the ElanFile."""
        return f"<ElanFile(elan_id={self.elan_id}, content_id={self.content_id}, project_id={self.project_id})>"
