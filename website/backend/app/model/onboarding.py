"""Onboarding state tracking for new installations.

This module provides the data model for tracking the onboarding progress
of new ELANORA installations, guiding administrators through the initial
setup of their first project, collaborator, and file upload.
"""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Enum as SQLEnum, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.database import Base


class OnboardingStep(StrEnum):
    """Steps in the onboarding workflow."""

    NOT_STARTED = "not_started"
    PROJECT_CREATED = "project_created"
    PROTOCOL_CONFIGURED = "protocol_configured"
    COLLABORATOR_INVITED = "collaborator_invited"
    FIRST_UPLOAD = "first_upload"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class OnboardingStatus(Base):
    """Tracks the onboarding progress for an installation.
    
    Each installation can have one onboarding status record that tracks
    which steps have been completed. This allows administrators to be guided
    through the initial setup process or to resume where they left off.
    """

    __tablename__ = "onboarding_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    instance_id: Mapped[int] = mapped_column(
        ForeignKey("INSTANCE.instance_id"), unique=True, nullable=False
    )
    current_step: Mapped[OnboardingStep] = mapped_column(
        SQLEnum(OnboardingStep),
        default=OnboardingStep.NOT_STARTED,
        nullable=False,
    )
    
    # Individual step completion flags for granular tracking
    project_created: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    protocol_configured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    collaborator_invited: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    first_upload: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Timestamps
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<OnboardingStatus(id={self.id}, instance_id={self.instance_id}, current_step={self.current_step.value})>"

    @property
    def is_complete(self) -> bool:
        """Check if all onboarding steps are complete."""
        return self.current_step == OnboardingStep.COMPLETE

    @property
    def is_skipped(self) -> bool:
        """Check if onboarding was skipped."""
        return self.current_step == OnboardingStep.SKIPPED

    @property
    def all_steps_complete(self) -> bool:
        """Check if all individual steps are marked complete."""
        return all([
            self.project_created,
            self.protocol_configured,
            self.collaborator_invited,
            self.first_upload,
        ])
