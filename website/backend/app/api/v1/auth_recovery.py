"""Verifying an account and recovering a forgotten password."""

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.limiter import limiter
from app.dependency.database import get_db_dep
from app.schema.requests.user import (
    ForgotPasswordRequest,
    ResetPasswordRequest,
    SendVerificationEmailRequest,
    VerifyEmailRequest,
)
from app.service import user_registration, user_verification
from app.service.outbox import (
    enqueue_account_verification_email,
    enqueue_password_reset_email,
)

router = APIRouter()


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
        user = await user_registration.get_user_by_email(db, body.email)

        if user:
            # Generate verification code
            verification_code = user_verification.generate_verification_code()
            hashed_code = user_verification.hash_verification_code(verification_code)

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
        result = await user_verification.reset_password(
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
        user = await user_registration.get_user_by_email(db, body.email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found.")

        if user.is_verified_account:
            raise HTTPException(status_code=400, detail="Account is already verified.")

        # Generate verification code
        verification_code = user_verification.generate_verification_code()
        hashed_code = user_verification.hash_verification_code(verification_code)

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
        result = await user_verification.verify_account(
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
