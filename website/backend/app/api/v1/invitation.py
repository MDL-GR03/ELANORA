"""Invitation API endpoints."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import authorize_project
from app.dependency.user import get_user_dep
from app.model.enums import ProjectPermission
from app.model.user import User, UserRole
from app.schema.requests.invitation import InvitationSendRequest
from app.schema.responses.invitation import (
    InvitationListResponse,
    InvitationSendResponse,
    InvitationValidationResponse,
)
from app.service.invitation import InvitationService

router = APIRouter()


@router.post("/send", response_model=InvitationSendResponse)
async def send_invitation(
    request: InvitationSendRequest,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> InvitationSendResponse:
    """Invite a member when the caller administers the target project."""
    access = await authorize_project(
        db,
        user,
        ProjectPermission.ADMIN,
        project_name=request.project_name,
    )
    if request.project_permission == ProjectPermission.OWNER:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Owner is a reserved permission",
        )
    if (
        access.permission == ProjectPermission.ADMIN
        and request.project_permission == ProjectPermission.ADMIN
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only an institution administrator can invite project administrators",
        )

    invitation_service = InvitationService()
    try:
        result = await invitation_service.send_invitation(
            db=db,
            sender_id=user.user_id,
            request=request,
        )
        # Commit the transaction
        await db.commit()
        return result
    except Exception:
        # Rollback in case of error
        await db.rollback()
        raise


@router.get("/validate/{invitation_code}", response_model=InvitationValidationResponse)
async def validate_invitation(
    invitation_code: str,
    db: AsyncSession = get_db_dep,
) -> InvitationValidationResponse:
    """Validate an invitation code (Public endpoint for registration)."""
    invitation_service = InvitationService()
    return await invitation_service.validate_invitation(
        db=db,
        invitation_code=invitation_code,
    )


@router.get("/sent", response_model=InvitationListResponse)
async def get_sent_invitations(
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> InvitationListResponse:
    """Get invitations sent by the current user (Admin only)."""
    # Check if user is admin
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can view sent invitations",
        )

    invitation_service = InvitationService()
    return await invitation_service.get_sent_invitations(
        db=db,
        sender_id=user.user_id,
    )


@router.get("/received/{email}", response_model=InvitationListResponse)
async def get_received_invitations(
    email: str,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> InvitationListResponse:
    """Get invitations received by email (Admin only or own email)."""
    # Check if user is admin or requesting their own invitations
    if user.role != UserRole.ADMIN and user.email != email:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own invitations",
        )

    invitation_service = InvitationService()
    return await invitation_service.get_user_invitations(
        db=db,
        email=email,
    )


@router.get("/project/{project_id}", response_model=InvitationListResponse)
async def get_project_invitations(
    project_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> InvitationListResponse:
    """Get invitations for a specific project (Admin only)."""
    await authorize_project(db, user, ProjectPermission.ADMIN, project_id=project_id)

    invitation_service = InvitationService()
    return await invitation_service.get_project_invitations(
        db=db,
        project_id=project_id,
    )


@router.get("/details/{invitation_id}")
async def get_invitation_details(
    invitation_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Get invitation details for the decision page (for authenticated users)."""
    invitation_service = InvitationService()
    return await invitation_service.get_invitation_details_for_user(
        db=db,
        invitation_id=invitation_id,
        user_id=user.user_id,
    )


@router.post("/accept/{invitation_id}")
async def accept_invitation(
    invitation_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Accept an invitation (for existing users)."""
    invitation_service = InvitationService()
    return await invitation_service.accept_invitation_by_user(
        db=db,
        invitation_id=invitation_id,
        user_id=user.user_id,
    )


@router.post("/reject/{invitation_id}")
async def reject_invitation(
    invitation_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Reject an invitation (for existing users)."""
    invitation_service = InvitationService()
    return await invitation_service.reject_invitation_by_user(
        db=db,
        invitation_id=invitation_id,
        user_id=user.user_id,
    )


@router.post("/resend/{invitation_id}")
async def resend_invitation(
    invitation_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Resend an invitation (Admin only)."""
    # Check if user is admin
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can resend invitations",
        )

    invitation_service = InvitationService()
    return await invitation_service.resend_invitation(
        db=db,
        invitation_id=invitation_id,
        sender_id=user.user_id,
    )


@router.post("/cancel/{invitation_id}")
async def cancel_invitation(
    invitation_id: int,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Cancel an invitation (Admin only)."""
    # Check if user is admin
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can cancel invitations",
        )

    invitation_service = InvitationService()
    return await invitation_service.cancel_invitation(
        db=db,
        invitation_id=invitation_id,
        sender_id=user.user_id,
    )
