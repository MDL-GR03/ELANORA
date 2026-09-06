from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class EffectiveNamingStandard(Base):
    __tablename__ = "EFFECTIVE_NAMING_STANDARD"
    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "project_file_type_id",
            "location_id",
            name="uq_project_filetype_location",
        ),
    )
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    project_file_type_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT_FILE_TYPE.id", ondelete="CASCADE"), nullable=False
    )
    naming_standard_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PROJECT_NAMING_STANDARD.id", ondelete="CASCADE"),
        nullable=False,
    )
    location_id: Mapped[int] = mapped_column(Integer, nullable=False)
