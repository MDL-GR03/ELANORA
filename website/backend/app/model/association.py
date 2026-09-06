from sqlalchemy import ForeignKey, ForeignKeyConstraint, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

from .enums import ProjectCapability, ProjectPermission

ELAN_FILE_ELANID_FK = "ELAN_FILE.elan_id"
PROJECT_PROJECTID_FK = "PROJECT.project_id"


class ElanFileToTier(Base):
    """Association table linking ELAN files to tiers."""

    __tablename__ = "ELAN_FILE_TO_TIER"

    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(ELAN_FILE_ELANID_FK), primary_key=True
    )
    tier_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("TIER.tier_id"), primary_key=True
    )


class ProjectAnnotStandard(Base):
    """Association table linking projects to annotation standards."""

    __tablename__ = "PROJECT_ANNOT_STANDARD"

    standard_id: Mapped[str] = mapped_column(
        String(50), ForeignKey("ANNOTATION_STANDARD.standard_id"), primary_key=True
    )
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(PROJECT_PROJECTID_FK), primary_key=True
    )


class UserToProject(Base):
    """Association table linking users to projects with permissions."""

    __tablename__ = "USER_TO_PROJECT"

    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey(PROJECT_PROJECTID_FK), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("USER.user_id"), primary_key=True
    )
    permission: Mapped[ProjectPermission] = mapped_column(
        String(20), nullable=False, default=ProjectPermission.READ
    )


class ProjectCapabilityGrant(Base):
    """A least-privilege capability delegated to one project member."""

    __tablename__ = "PROJECT_CAPABILITY_GRANT"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["USER_TO_PROJECT.project_id", "USER_TO_PROJECT.user_id"],
            ondelete="CASCADE",
            name="fk_capability_project_membership",
        ),
    )

    project_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    capability: Mapped[ProjectCapability] = mapped_column(String(50), primary_key=True)


class ElanFileToMedia(Base):
    """Association table linking ELAN files to media."""

    __tablename__ = "ELAN_FILE_TO_MEDIA"

    elan_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("ELAN_FILE.elan_id", ondelete="CASCADE"), primary_key=True
    )
    media_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("ELAN_FILE_MEDIA.media_id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Relationships
    elan_file = relationship("ElanFile", back_populates="media_links")
    media = relationship("ElanFileMedia", back_populates="elan_files")
