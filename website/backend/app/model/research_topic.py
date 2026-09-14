from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class ResearchTopic(Base):
    """Reusable project research scope expressed as a set of tier names."""

    __tablename__ = "RESEARCH_TOPIC"

    topic_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("PROJECT.project_id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    allow_new_tiers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    tiers: Mapped[list["ResearchTopicTier"]] = relationship(
        back_populates="topic", cascade="all, delete-orphan", lazy="selectin"
    )

    __table_args__ = (
        CheckConstraint("btrim(name) <> ''", name="ck_research_topic_name_nonblank"),
        UniqueConstraint("project_id", "name", name="uq_research_topic_project_name"),
        Index(
            "uq_research_topic_project_normalized_name",
            "project_id",
            func.lower(func.regexp_replace(func.btrim(name), r"\s+", " ", "g")),
            unique=True,
        ),
        Index("ix_research_topic_project", "project_id"),
    )


class ResearchTopicTier(Base):
    __tablename__ = "RESEARCH_TOPIC_TIER"
    __table_args__ = (
        CheckConstraint(
            "btrim(tier_name) <> ''", name="ck_research_topic_tier_name_nonblank"
        ),
    )

    topic_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("RESEARCH_TOPIC.topic_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tier_name: Mapped[str] = mapped_column(String(255), primary_key=True)
    topic: Mapped[ResearchTopic] = relationship(back_populates="tiers")


class ProjectBaselineTier(Base):
    """A project-wide context tier included in every scoped research copy."""

    __tablename__ = "PROJECT_BASELINE_TIER"
    __table_args__ = (
        CheckConstraint(
            "btrim(tier_name) <> ''", name="ck_project_baseline_tier_name_nonblank"
        ),
    )

    project_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("PROJECT.project_id", ondelete="CASCADE"),
        primary_key=True,
    )
    tier_name: Mapped[str] = mapped_column(String(255), primary_key=True)
