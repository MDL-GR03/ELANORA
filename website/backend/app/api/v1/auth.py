import secrets
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import (
    ACCESS_TOKEN_COOKIE_NAME,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_SECURE,
    CSRF_TOKEN_NAME,
    LEGACY_REFRESH_TOKEN_PATH,
    REFRESH_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_EXPIRE_DAYS,
    REFRESH_TOKEN_PATH,
)
from app.core.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.core.limiter import limiter
from app.crud.project import get_project_by_id
from app.dependency.database import get_db_dep
from app.schema.common.token import TokenData
from app.schema.requests.register_with_invitation import RegisterWithInvitationRequest
from app.schema.requests.user import (
    ForgotPasswordRequest,
    LoginRequest,
    ResetPasswordRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
)
from app.schema.responses.user import LoginResponse, RegistrationResponse, UserResponse
from app.service.invitation import InvitationService
from app.service.outbox import (
    enqueue_account_verification_email,
    enqueue_password_reset_email,
)
from app.service.refresh_session import (
    create_refresh_session,
    revoke_refresh_session,
)
from app.service.user import UserService

router = APIRouter()


def _clear_auth_cookies(response: Response) -> None:
    """Expire every browser credential using its original cookie path."""
    response.delete_cookie(ACCESS_TOKEN_COOKIE_NAME)
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path=REFRESH_TOKEN_PATH)
    response.delete_cookie(REFRESH_TOKEN_COOKIE_NAME, path=LEGACY_REFRESH_TOKEN_PATH)
    response.delete_cookie(CSRF_TOKEN_NAME)


@router.post("/login", response_model=LoginResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginRequest,
    response: Response,
    db: AsyncSession = get_db_dep,
) -> LoginResponse:
    """Handle user login and set JWT tokens as HTTP-only cookies."""
    # Use service layer for authentication
    login_result = await UserService.login_user(
        db=db,
        login_or_email=body.login,
        password=body.password,
    )

    if not login_result["success"]:
        raise HTTPException(status_code=400, detail=login_result["message"])

    # Handle email verification case
    if login_result.get("needs_verification"):
        return LoginResponse(
            message=login_result["message"],
            user=None,
            csrf_token="",
            needs_verification=True,
            email=login_result["email"],
        )

    # Get user and create tokens
    user = login_result["user"]
    session_id = uuid.uuid4()
    token_data = TokenData(
        sub=str(user.user_id),
        session_id=str(session_id),
        token_id=secrets.token_hex(16),
    )

    # Create tokens
    access_token = create_access_token(data=token_data)
    refresh_token = create_refresh_token(data=token_data)
    csrf_token = secrets.token_hex(16)
    await create_refresh_session(db, user.user_id, session_id, refresh_token)
    await db.commit()

    # Set cookies
    response.set_cookie(
        ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"

    response.set_cookie(
        REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path=REFRESH_TOKEN_PATH,
    )

    response.set_cookie(
        CSRF_TOKEN_NAME,
        csrf_token,
        # The CSRF token must outlive the access token because the protected
        # refresh endpoint needs it to issue the next access token.
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        httponly=False,
        secure=COOKIE_SECURE,
        samesite="lax",
    )

    user_response = UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified_account=user.is_verified_account,
        created_at=user.created_at,
    )

    return LoginResponse(
        message="Login successful, cookies set.",
        user=user_response,
        csrf_token=csrf_token,
    )


@router.post("/refresh")
async def refresh_tokens(
    request: Request, response: Response, db: AsyncSession = get_db_dep
) -> dict[str, Any]:
    """Refresh the access token using the refresh token."""
    # Get refresh token from cookies
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not refresh_token:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token is missing"
        )

    try:
        # Use service layer for token refresh
        refresh_result = await UserService.refresh_user_tokens(db, refresh_token)

        if not refresh_result["success"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=refresh_result["message"],
            )

        # Set new cookies
        response.set_cookie(
            ACCESS_TOKEN_COOKIE_NAME,
            refresh_result["access_token"],
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"

        response.set_cookie(
            REFRESH_TOKEN_COOKIE_NAME,
            refresh_result["refresh_token"],
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            path=REFRESH_TOKEN_PATH,
        )

        response.set_cookie(
            CSRF_TOKEN_NAME,
            refresh_result["csrf_token"],
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=False,
            secure=COOKIE_SECURE,
            samesite="lax",
        )

        return {
            "message": "Tokens refreshed successfully",
            CSRF_TOKEN_NAME: refresh_result["csrf_token"],
        }

    except HTTPException:
        # Clear invalid tokens
        _clear_auth_cookies(response)
        raise
    except Exception as e:
        _clear_auth_cookies(response)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Failed to refresh tokens"
        ) from e


@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Clear browser credentials even if the access token has expired."""
    refresh_token = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if refresh_token:
        try:
            token_data = verify_refresh_token(refresh_token)
            if token_data.session_id:
                await revoke_refresh_session(db, uuid.UUID(token_data.session_id))
        except (HTTPException, ValueError):
            pass
    _clear_auth_cookies(response)
    response.headers["Cache-Control"] = "no-store"
    return {"message": "Logged out successfully, cookies cleared."}


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


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Request a password reset via email.

    This endpoint allows a user to request a password reset by providing their email address.
    A verification code will be sent via email if the address exists in the database.

    Args:
        request (Request): The HTTP Request object (required by SlowAPI for rate limiting)
        body (ForgotPasswordRequest): Form data containing email and language
        db (AsyncSession): Database session

    Returns:
        dict[str, Any]: JSON response with a confirmation message

    Raises:
        HTTPException: If an error occurs during request processing

    Note:
        For security reasons, the same response is returned whether the email exists or not
        in the database.

    """
    try:
        # Check if user exists
        user = await UserService.get_user_by_email(db, body.email)

        if user:
            # Generate verification code
            verification_code = UserService._generate_verification_code()
            hashed_code = UserService._hash_verification_code(verification_code)

            # Store the hash and encrypted delivery request atomically.
            user.activation_code = hashed_code
            await enqueue_password_reset_email(
                db,
                user_id=user.user_id,
                email=user.email,
                username=user.username,
                code=verification_code,
                language=body.language,
            )
            await db.commit()

        # Always return the same response for security
        return {
            "message": "If the email address exists in our system, you will receive a password reset code shortly.",
            "success": True,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unable to process request",
        ) from e


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Reset user password with verification code.

    This endpoint allows a user to reset their password using the verification code
    sent via email.

    Args:
        request (Request): The HTTP Request object (required by SlowAPI for rate limiting)
        body (ResetPasswordRequest): Form data containing email, code, and new password
        db (AsyncSession): Database session

    Returns:
        dict[str, Any]: JSON response with success or error message

    Raises:
        HTTPException: If the reset code is invalid or user is not found

    """
    try:
        # Reset password using the service
        result = await UserService.reset_password(
            db=db,
            email=body.email,
            reset_code=body.code,
            new_password=body.new_password,
        )

        if result["success"]:
            return {
                "message": "Password reset successfully. You can now log in with your new password.",
                "success": True,
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail="Unable to reset password",
        ) from e


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


@router.post("/send-verification-email")
@limiter.limit("3/minute")
async def send_verification_email(
    request: Request,
    body: SendVerificationEmailRequest,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Send email verification code to user.

    This endpoint allows sending a verification code to verify a user's email address.
    A verification code will be sent via email if the address exists in the database
    and the account is not already verified.

    Args:
        request (Request): The HTTP Request object (required by SlowAPI for rate limiting)
        body (SendVerificationEmailRequest): Form data containing email and language
        db (AsyncSession): Database session

    Returns:
        dict[str, Any]: JSON response with a confirmation message

    Raises:
        HTTPException: If an error occurs during request processing

    """
    try:
        # Check if user exists
        user = await UserService.get_user_by_email(db, body.email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if user.is_verified_account:
            raise HTTPException(status_code=400, detail="Account is already verified.")

        # Generate verification code
        verification_code = UserService._generate_verification_code()
        hashed_code = UserService._hash_verification_code(verification_code)

        # Store the hash and encrypted delivery request atomically.
        user.activation_code = hashed_code
        await enqueue_account_verification_email(
            db,
            user_id=user.user_id,
            email=user.email,
            username=user.username,
            code=verification_code,
            language=body.language,
        )
        await db.commit()

        return {
            "message": "Verification code sent to your email address.",
            "success": True,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Unable to process request",
        ) from e


@router.post("/verify-email")
@limiter.limit("5/minute")
async def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: AsyncSession = get_db_dep,
) -> dict[str, Any]:
    """Verify user email with verification code.

    This endpoint allows a user to verify their email address using the verification code
    sent via email.

    Args:
        request (Request): The HTTP Request object (required by SlowAPI for rate limiting)
        body (VerifyEmailRequest): Form data containing email and verification code
        db (AsyncSession): Database session

    Returns:
        dict[str, Any]: JSON response with success or error message

    Raises:
        HTTPException: If the verification code is invalid or user is not found

    """
    try:
        # Verify email using the service
        result = await UserService.verify_account(
            db=db,
            email=body.email,
            verification_code=body.code,
        )

        if result["success"]:
            return {
                "message": "Email verified successfully. You can now access all features.",
                "success": True,
            }
        else:
            raise HTTPException(status_code=400, detail=result["message"])

    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=500,
            detail="Unable to verify email",
        ) from e
