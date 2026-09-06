from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class ProjectLocationFileType(Base):
    __tablename__ = "PROJECT_LOCATION_FILE_TYPE"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "location_id",
            "project_file_type_id",
            name="uq_project_location_filetype",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)
    project_file_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT_FILE_TYPE.id", ondelete="CASCADE"), nullable=False
    )
