"""Response schemas for onboarding endpoints.

These schemas define the response bodies for the onboarding API endpoints,
providing structured data about the onboarding status and progress.
"""

from datetime import datetime

from pydantic import BaseModel

from app.model.onboarding import OnboardingStep


class OnboardingStatusResponse(BaseModel):
    """Response containing the current onboarding status for an installation."""

    id: int
    instance_id: int
    current_step: OnboardingStep
    project_created: bool
    protocol_configured: bool
    collaborator_invited: bool
    first_upload: bool
    completed: bool
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class OnboardingProgressResponse(BaseModel):
    """Response containing detailed progress information for the onboarding workflow."""

    current_step: OnboardingStep
    steps_completed: int
    total_steps: int
    completion_percentage: float
    next_step: OnboardingStep | None = None
    next_step_description: str | None = None


class StartOnboardingResponse(BaseModel):
    """Response after starting the onboarding workflow."""

    message: str
    onboarding_id: int
    current_step: OnboardingStep


class MarkStepCompleteResponse(BaseModel):
    """Response after marking a step as complete."""

    message: str
    current_step: OnboardingStep
    all_steps_complete: bool


class SkipOnboardingResponse(BaseModel):
    """Response after skipping the onboarding workflow."""

    message: str
    onboarding_skipped: bool


class OnboardingStepInfo(BaseModel):
    """Information about a specific onboarding step."""

    step_id: str
    title: str
    description: str
    completed: bool
    order: int
