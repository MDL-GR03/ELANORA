"""Registering an account and checking a name or address is free."""

from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.project import get_project_by_id
from app.dependency.database import get_db_dep
from app.schema.requests.register_with_invitation import RegisterWithInvitationRequest
from app.schema.responses.user import RegistrationResponse
from app.service.invitation import InvitationService
from app.service.user import UserService

router = APIRouter()


@router.post("/register", response_model=RegistrationResponse)
async def register(
    request: RegisterWithInvitationRequest,
    db: AsyncSession = get_db_dep,
) -> RegistrationResponse:
    """Register a new user using an invitation code.

    This endpoint allows a user to register using an invitation code.
    It validates the invitation code, creates the user, and marks the invitation as used.

    Args:
        request (RegisterWithInvitationRequest): The request body containing user details and invitation code.
        db (AsyncSession): Database session.

    Returns:
        UserResponse: The registered user details.

    Raises:
        HTTPException: If the invitation code is invalid or expired, or if user creation fails.

    """
    invitation_service = InvitationService()
    user_service = UserService()

    # 1. Validate the invitation code
    invitation_validation = await invitation_service.validate_invitation(
        db, request.invitation_code
    )
    if not invitation_validation.valid or not invitation_validation.invitation:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation invalide ou expirée.",
        )

    invitation_info = invitation_validation.invitation
    project = await get_project_by_id(db, invitation_info.project_id)
    if project is None:
        raise HTTPException(
            status_code=400, detail="Invitation project no longer exists."
        )
    # check if the email in the invitation matches the one in the request (if provided)
    if (
        invitation_info.receiver_email
        and request.email
        and invitation_info.receiver_email.strip().lower()
        != request.email.strip().lower()
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="L'email du formulaire ne correspond pas à celui de l'invitation.",
        )

    # 2. Create the user
    # Registration requires the exact email bound to the invitation, so that
    # successful redemption is itself proof of control of the invited address.
    is_verified = True

    # Create user using UserService
    user = await user_service.create_user(
        db=db,
        username=request.username,
        email=request.email,
        password=request.password,
        first_name=request.first_name,
        last_name=request.last_name,
        affiliation=request.affiliation,
        department=request.department,
        instance_id=project.instance_id,
        is_verified=is_verified,
        phone_number=request.phone_number,
        address_data=request.address,
        commit=False,
    )
    # 3. Accept the invitation
    accepted = await invitation_service.accept_invitation(
        db,
        invitation_info.invitation_id,
        user.user_id,
        commit=False,
    )
    if not accepted:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation could not be redeemed. No account was created.",
        )
    await db.commit()
    await invitation_service.notify_project_admins_member_joined(
        db, invitation_info.project_id, user
    )

    # 4. Return the registration response
    return RegistrationResponse(
        message="Account created successfully",
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        requires_activation=not is_verified,
    )


@router.get("/check-username/{username}")
async def check_username_availability(
    username: str,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Check if a username is available for registration."""
    try:
        available = await UserService.check_username_availability(db, username)
        return {
            "available": available,
            "message": "Username is available"
            if available
            else "Username is already taken",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Unable to check username availability"
        ) from e


@router.get("/check-email/{email}")
async def check_email_availability(
    email: str,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Check if an email is available for registration."""
    try:
        available = await UserService.check_email_availability(db, email)
        return {
            "available": available,
            "message": "Email is available" if available else "Email is already in use",
        }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail="Unable to check email availability"
        ) from e
