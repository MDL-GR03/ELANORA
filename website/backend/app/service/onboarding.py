"""Onboarding service for managing the onboarding workflow.

This service handles the business logic for tracking and updating onboarding
progress, including:
- Starting the onboarding workflow
- Marking steps as complete
- Skipping the onboarding
- Retrieving current status
- Calculating progress
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.model.instance import Instance
from app.model.onboarding import OnboardingStep, OnboardingStatus
from app.model.user import User


class OnboardingService:
    """Service for managing onboarding workflow state."""

    @staticmethod
    async def get_onboarding_status(
        db: AsyncSession, instance_id: int
    ) -> OnboardingStatus | None:
        """Retrieve the onboarding status for a specific instance."""
        return await db.scalar(
            select(OnboardingStatus).where(
                OnboardingStatus.instance_id == instance_id
            )
        )

    @staticmethod
    async def get_or_create_onboarding_status(
        db: AsyncSession, instance_id: int
    ) -> OnboardingStatus:
        """Get existing onboarding status or create a new one if it doesn't exist."""
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        if status is not None:
            return status

        # Create new onboarding status
        status = OnboardingStatus(instance_id=instance_id)
        db.add(status)
        await db.flush()
        return status

    @staticmethod
    async def start_onboarding(
        db: AsyncSession, instance_id: int
    ) -> OnboardingStatus:
        """Start the onboarding workflow for an instance.
        
        Creates a new onboarding status record if one doesn't exist,
        or resets an existing one to start from the beginning.
        """
        # Verify the instance exists
        instance = await db.scalar(
            select(Instance).where(Instance.instance_id == instance_id)
        )
        if instance is None:
            raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)

        # Get or create onboarding status
        status = await OnboardingService.get_or_create_onboarding_status(db, instance_id)
        
        # Reset to starting state
        status.current_step = OnboardingStep.NOT_STARTED
        status.project_created = False
        status.protocol_configured = False
        status.collaborator_invited = False
        status.first_upload = False
        status.completed_at = None
        status.updated_at = datetime.now()
        
        await db.commit()
        return status

    @staticmethod
    async def mark_step_complete(
        db: AsyncSession, instance_id: int, step: OnboardingStep
    ) -> OnboardingStatus:
        """Mark a specific onboarding step as complete.
        
        Updates the current step and the corresponding completion flag.
        If all steps are complete, marks the onboarding as complete.
        """
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        if status is None:
            # If no status exists, start onboarding first
            status = await OnboardingService.start_onboarding(db, instance_id)

        # Update the specific step flag
        if step == OnboardingStep.PROJECT_CREATED:
            status.project_created = True
        elif step == OnboardingStep.PROTOCOL_CONFIGURED:
            status.protocol_configured = True
        elif step == OnboardingStep.COLLABORATOR_INVITED:
            status.collaborator_invited = True
        elif step == OnboardingStep.FIRST_UPLOAD:
            status.first_upload = True

        # Update current step
        status.current_step = step
        status.updated_at = datetime.now()

        # Check if all steps are complete
        if status.all_steps_complete:
            status.current_step = OnboardingStep.COMPLETE
            status.completed_at = datetime.now()

        await db.commit()
        return status

    @staticmethod
    async def skip_onboarding(
        db: AsyncSession, instance_id: int
    ) -> OnboardingStatus:
        """Skip the onboarding workflow entirely."""
        status = await OnboardingService.get_or_create_onboarding_status(db, instance_id)
        
        status.current_step = OnboardingStep.SKIPPED
        status.completed_at = datetime.now()
        status.updated_at = datetime.now()
        
        await db.commit()
        return status

    @staticmethod
    async def update_step_flags(
        db: AsyncSession,
        instance_id: int,
        project_created: bool | None = None,
        protocol_configured: bool | None = None,
        collaborator_invited: bool | None = None,
        first_upload: bool | None = None,
    ) -> OnboardingStatus:
        """Update individual step completion flags.
        
        Allows for granular updates to the step flags without changing
        the current step.
        """
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        if status is None:
            status = await OnboardingService.start_onboarding(db, instance_id)

        if project_created is not None:
            status.project_created = project_created
        if protocol_configured is not None:
            status.protocol_configured = protocol_configured
        if collaborator_invited is not None:
            status.collaborator_invited = collaborator_invited
        if first_upload is not None:
            status.first_upload = first_upload

        status.updated_at = datetime.now()

        # Update current step based on progress
        if not any([
            status.project_created,
            status.protocol_configured,
            status.collaborator_invited,
            status.first_upload,
        ]):
            status.current_step = OnboardingStep.NOT_STARTED
        elif status.project_created and not status.protocol_configured:
            status.current_step = OnboardingStep.PROJECT_CREATED
        elif status.protocol_configured and not status.collaborator_invited:
            status.current_step = OnboardingStep.PROTOCOL_CONFIGURED
        elif status.collaborator_invited and not status.first_upload:
            status.current_step = OnboardingStep.COLLABORATOR_INVITED
        elif status.first_upload:
            status.current_step = OnboardingStep.FIRST_UPLOAD

        # Check if all steps are complete
        if status.all_steps_complete:
            status.current_step = OnboardingStep.COMPLETE
            status.completed_at = datetime.now()

        await db.commit()
        return status

    @staticmethod
    async def get_onboarding_progress(
        db: AsyncSession, instance_id: int
    ) -> dict:
        """Get detailed progress information for the onboarding workflow.
        
        Returns a dictionary with progress metrics.
        """
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        
        if status is None:
            return {
                "current_step": OnboardingStep.NOT_STARTED,
                "steps_completed": 0,
                "total_steps": 4,
                "completion_percentage": 0.0,
                "next_step": OnboardingStep.PROJECT_CREATED,
                "next_step_description": None,
            }

        steps = [
            OnboardingStep.PROJECT_CREATED,
            OnboardingStep.PROTOCOL_CONFIGURED,
            OnboardingStep.COLLABORATOR_INVITED,
            OnboardingStep.FIRST_UPLOAD,
        ]

        steps_completed = sum([
            status.project_created,
            status.protocol_configured,
            status.collaborator_invited,
            status.first_upload,
        ])

        completion_percentage = (steps_completed / len(steps)) * 100

        # Find next incomplete step
        next_step = None
        if not status.project_created:
            next_step = OnboardingStep.PROJECT_CREATED
        elif not status.protocol_configured:
            next_step = OnboardingStep.PROTOCOL_CONFIGURED
        elif not status.collaborator_invited:
            next_step = OnboardingStep.COLLABORATOR_INVITED
        elif not status.first_upload:
            next_step = OnboardingStep.FIRST_UPLOAD

        return {
            "current_step": status.current_step,
            "steps_completed": steps_completed,
            "total_steps": len(steps),
            "completion_percentage": completion_percentage,
            "next_step": next_step,
            "next_step_description": None,
        }

    @staticmethod
    async def is_onboarding_complete(
        db: AsyncSession, instance_id: int
    ) -> bool:
        """Check if onboarding is complete for an instance."""
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        return status is not None and status.is_complete

    @staticmethod
    async def is_onboarding_skipped(
        db: AsyncSession, instance_id: int
    ) -> bool:
        """Check if onboarding was skipped for an instance."""
        status = await OnboardingService.get_onboarding_status(db, instance_id)
        return status is not None and status.is_skipped
