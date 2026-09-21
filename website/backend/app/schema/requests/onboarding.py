"""Request schemas for onboarding endpoints.

These schemas define the request bodies for the onboarding API endpoints,
validating the data required for tracking and updating onboarding progress.
"""

from enum import StrEnum

from pydantic import BaseModel


class OnboardingStepRequest(StrEnum):
    """Enum for onboarding step identifiers in API requests."""

    NOT_STARTED = "not_started"
    PROJECT_CREATED = "project_created"
    PROTOCOL_CONFIGURED = "protocol_configured"
    COLLABORATOR_INVITED = "collaborator_invited"
    FIRST_UPLOAD = "first_upload"
    COMPLETE = "complete"
    SKIPPED = "skipped"


class StartOnboardingRequest(BaseModel):
    """Request to start the onboarding workflow for an installation."""

    pass  # Empty body - just trigger onboarding start


class MarkStepCompleteRequest(BaseModel):
    """Request to mark a specific onboarding step as complete."""

    step: OnboardingStepRequest


class SkipOnboardingRequest(BaseModel):
    """Request to skip the onboarding workflow entirely."""

    pass  # Empty body - just trigger skip


class UpdateOnboardingStepFlagsRequest(BaseModel):
    """Request to update individual step completion flags."""

    project_created: bool | None = None
    protocol_configured: bool | None = None
    collaborator_invited: bool | None = None
    first_upload: bool | None = None
