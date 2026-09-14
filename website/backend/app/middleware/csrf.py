from collections.abc import Awaitable, Callable

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.centralized_logging import get_logger

csrf_logger = get_logger()


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce CSRF protection by validating tokens in headers and cookies."""

    def __init__(self, app: ASGIApp, exclude_paths: list[str] | None = None):
        """Initialize CSRFMiddleware with optional list of excluded paths."""
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/api/v1/auth/login",
            "/api/v1/auth/register",
            "/api/v1/auth/forgot-password",
            "/api/v1/auth/reset-password",
            "/api/v1/auth/send-verification-email",
            "/api/v1/auth/verify-email",
            "/api/v1/setup/initialize",
            "/api/v1/contact/",
        ]

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """Process incoming requests and enforce CSRF checks unless excluded."""
        # Never trust Referer or fetch-metadata headers as an authentication
        # signal: clients can forge them. Only explicit public paths and
        # non-mutating methods bypass the double-submit check.
        if (
            request.method in ["GET", "HEAD", "OPTIONS"]
            or request.url.path in self.exclude_paths
        ):
            return await call_next(request)

        # Get the CSRF token from the header
        csrf_header = request.headers.get("X-CSRF-Token")
        # Get the CSRF token from the cookie
        csrf_cookie = request.cookies.get("elanora_csrf")

        # Verify the CSRF token matches
        if not csrf_header or not csrf_cookie or csrf_header != csrf_cookie:
            csrf_logger.warning(
                "CSRF validation failed",
                extra={"method": request.method, "path": request.url.path},
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF token missing or invalid."},
            )

        # Continue with the request
        return await call_next(request)
