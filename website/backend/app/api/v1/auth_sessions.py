"""Signing in, refreshing a session and signing out."""

import secrets
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
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
from app.core.errors import ElanoraError, ErrorCode
from app.core.jwt import create_access_token, create_refresh_token, verify_refresh_token
from app.core.limiter import limiter
from app.dependency.database import get_db_dep
from app.schema.common.token import TokenData
from app.schema.requests.user import (
    LoginRequest,
)
from app.schema.responses.user import LoginResponse, UserResponse
from app.service import user_sessions
from app.service.refresh_session import (
    create_refresh_session,
    revoke_refresh_session,
)

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
    outcome = await user_sessions.login_user(
        db=db,
        login_or_email=body.login,
        password=body.password,
    )
    user = outcome.user
    if outcome.needs_verification:
        return LoginResponse(
            message="Email verification required",
            user=None,
            csrf_token="",
            needs_verification=True,
            email=user.email,
        )

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
        raise ElanoraError(ErrorCode.REFRESH_TOKEN_MISSING)

    try:
        tokens = await user_sessions.refresh_user_tokens(db, refresh_token)

        # Set new cookies
        response.set_cookie(
            ACCESS_TOKEN_COOKIE_NAME,
            tokens.access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
        )
        response.headers["Cache-Control"] = "no-store"

        response.set_cookie(
            REFRESH_TOKEN_COOKIE_NAME,
            tokens.refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=COOKIE_SECURE,
            samesite="lax",
            path=REFRESH_TOKEN_PATH,
        )

        response.set_cookie(
            CSRF_TOKEN_NAME,
            tokens.csrf_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=False,
            secure=COOKIE_SECURE,
            samesite="lax",
        )

        return {
            "message": "Tokens refreshed successfully",
            CSRF_TOKEN_NAME: tokens.csrf_token,
        }

    except (HTTPException, ElanoraError):
        # Clear invalid tokens
        _clear_auth_cookies(response)
        raise
    except Exception as e:
        _clear_auth_cookies(response)
        raise ElanoraError(ErrorCode.SESSION_REFRESH_FAILED) from e


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
