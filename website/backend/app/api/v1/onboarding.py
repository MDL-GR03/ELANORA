"""Onboarding endpoints for guided first-time setup.

These endpoints provide the API for tracking and managing the onboarding
workflow, allowing administrators to be guided through the initial setup
of their ELANORA installation.
"""

from typing import cast

from fastapi import APIRouter, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep, get_user_dep
from app.model.onboarding import OnboardingStep
from app.model.user import User
from app.schema.requests.onboarding import (
    MarkStepCompleteRequest,
    UpdateOnboardingStepFlagsRequest,
)
from app.schema.responses.onboarding import (
    MarkStepCompleteResponse,
    OnboardingProgressResponse,
    OnboardingStatusResponse,
    SkipOnboardingResponse,
    StartOnboardingResponse,
)
from app.service.onboarding import OnboardingService

router = APIRouter()


@router.get(
    "/status",
    response_model=OnboardingStatusResponse | None,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Instance not found"},
    },
)
async def get_onboarding_status(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
) -> OnboardingStatusResponse | None:
    """Get the current onboarding status for this installation.

    Returns the onboarding progress for the current instance, or null if
    onboarding has not been started yet.
    """
    instance_id = current_user.instance_id
    status = await OnboardingService.get_onboarding_status(db, instance_id)

    if status is None:
        return None

    return OnboardingStatusResponse(
        id=status.id,
        instance_id=status.instance_id,
        current_step=status.current_step,
        project_created=status.project_created,
        protocol_configured=status.protocol_configured,
        collaborator_invited=status.collaborator_invited,
        first_upload=status.first_upload,
        completed=status.is_complete,
        completed_at=status.completed_at,
        created_at=status.created_at,
        updated_at=status.updated_at,
    )


@router.get(
    "/progress",
    response_model=OnboardingProgressResponse,
)
async def get_onboarding_progress(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
) -> OnboardingProgressResponse:
    """Get detailed progress information for the onboarding workflow.

    Returns completion percentage, steps completed, and next step information.
    """
    instance_id = current_user.instance_id
    progress = await OnboardingService.get_onboarding_progress(db, instance_id)

    return OnboardingProgressResponse(
        current_step=cast("OnboardingStep", progress["current_step"]),
        steps_completed=cast("int", progress["steps_completed"]),
        total_steps=cast("int", progress["total_steps"]),
        completion_percentage=cast("float", progress["completion_percentage"]),
        next_step=cast("OnboardingStep | None", progress["next_step"]),
        next_step_description=cast("str | None", progress["next_step_description"]),
    )


@router.post(
    "/start",
    response_model=StartOnboardingResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Instance not found"},
        status.HTTP_403_FORBIDDEN: {"description": "Admin access required"},
    },
)
async def start_onboarding(
    db: AsyncSession = get_db_dep,
    current_user: User = get_admin_dep,
) -> StartOnboardingResponse:
    """Start the onboarding workflow for this installation.

    Creates a new onboarding status record or resets an existing one.
    Only available to administrators.
    """
    instance_id = current_user.instance_id
    status = await OnboardingService.start_onboarding(db, instance_id)

    return StartOnboardingResponse(
        message="Onboarding started successfully",
        onboarding_id=status.id,
        current_step=status.current_step,
    )


@router.post(
    "/step/complete",
    response_model=MarkStepCompleteResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Instance not found"},
        status.HTTP_400_BAD_REQUEST: {"description": "Invalid step"},
    },
)
async def mark_step_complete(
    body: MarkStepCompleteRequest,
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
) -> MarkStepCompleteResponse:
    """Mark a specific onboarding step as complete.

    Updates the current step and checks if all steps are now complete.
    """
    instance_id = current_user.instance_id

    # Convert string enum to OnboardingStep
    try:
        step = OnboardingStep(body.step.value)
    except ValueError:
        # Try direct conversion
        try:
            step = OnboardingStep(body.step)
        except ValueError:
            step = OnboardingStep.NOT_STARTED

    status = await OnboardingService.mark_step_complete(db, instance_id, step)

    return MarkStepCompleteResponse(
        message=f"Step {step.value} marked as complete",
        current_step=status.current_step,
        all_steps_complete=status.all_steps_complete,
    )


@router.post(
    "/skip",
    response_model=SkipOnboardingResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Instance not found"},
    },
)
async def skip_onboarding(
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
) -> SkipOnboardingResponse:
    """Skip the onboarding workflow entirely.

    Marks the onboarding as skipped for this installation.
    """
    instance_id = current_user.instance_id
    status = await OnboardingService.skip_onboarding(db, instance_id)

    return SkipOnboardingResponse(
        message="Onboarding skipped",
        onboarding_skipped=status.is_skipped,
    )


@router.patch(
    "/status",
    response_model=OnboardingStatusResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Instance not found"},
    },
)
async def update_step_flags(
    body: UpdateOnboardingStepFlagsRequest,
    db: AsyncSession = get_db_dep,
    current_user: User = get_user_dep,
) -> OnboardingStatusResponse:
    """Update individual step completion flags.

    Allows for granular updates to the step flags without changing
    the current step. This is useful when steps are completed through
    other means (e.g., creating a project through the normal UI).
    """
    instance_id = current_user.instance_id
    status = await OnboardingService.update_step_flags(
        db,
        instance_id,
        project_created=body.project_created,
        protocol_configured=body.protocol_configured,
        collaborator_invited=body.collaborator_invited,
        first_upload=body.first_upload,
    )

    return OnboardingStatusResponse(
        id=status.id,
        instance_id=status.instance_id,
        current_step=status.current_step,
        project_created=status.project_created,
        protocol_configured=status.protocol_configured,
        collaborator_invited=status.collaborator_invited,
        first_upload=status.first_upload,
        completed=status.is_complete,
        completed_at=status.completed_at,
        created_at=status.created_at,
        updated_at=status.updated_at,
    )
