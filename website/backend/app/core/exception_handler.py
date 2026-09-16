import logging
import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.status import HTTP_400_BAD_REQUEST

from app.core.logging import get_stream_logger

# Try to import config, but don't fail if it's not available
try:
    from app.core.config import (
        EXCEPTION_LOG_LEVEL as CONFIG_LOG_LEVEL,
    )

    EXCEPTION_LOG_LEVEL = CONFIG_LOG_LEVEL
    HAS_CONFIG = True
    if not EXCEPTION_LOG_LEVEL:
        EXCEPTION_LOG_LEVEL = "WARNING"
except ImportError:
    HAS_CONFIG = False


def get_exception_logger(logger_name: str) -> logging.Logger:
    """Get a logger for exception handling with consistent configuration."""
    # Use config if available, fallback to environment variables
    level = EXCEPTION_LOG_LEVEL if HAS_CONFIG else "WARNING"

    return get_stream_logger(
        logger_name=f"elanora.exceptions.{logger_name}",
        level=level,
    )


def get_client_info(request: Request) -> dict[str, str]:
    """Extract the non-sensitive request context needed for diagnostics."""
    return {
        "method": request.method,
        "path": request.url.path,
        "correlation_id": getattr(request.state, "correlation_id", str(uuid.uuid4())),
    }


def _public_validation_errors(
    exc: RequestValidationError,
) -> list[dict[str, Any]]:
    """Return stable validation diagnostics without echoing submitted values."""
    return [
        {
            "type": error.get("type", "validation_error"),
            "loc": list(error.get("loc", ())),
            "msg": "Invalid request value.",
        }
        for error in exc.errors()
    ]


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Handle validation errors raised by FastAPI and returns a JSON response with error details."""
    if isinstance(exc, RequestValidationError):
        validation_logger = get_exception_logger("validation")
        client_info = get_client_info(request)

        public_errors = _public_validation_errors(exc)
        validation_logger.error(
            "Validation error occurred",
            extra={
                "event_type": "validation_error",
                "method": client_info["method"],
                "path": client_info["path"],
                "correlation_id": client_info["correlation_id"],
                "validation_error_types": [item["type"] for item in public_errors],
                "error_count": len(public_errors),
            },
        )

        return JSONResponse(
            status_code=HTTP_400_BAD_REQUEST,
            content={
                "detail": public_errors,
                "code": "validation_error",
                "correlation_id": client_info["correlation_id"],
            },
        )
    raise exc


async def rate_limit_exception_handler(request: Request, exc: Exception) -> Response:
    """Handle rate limit exceptions and log details before delegating to the default handler."""
    if isinstance(exc, RateLimitExceeded):
        rate_limit_logger = get_exception_logger("rate_limit")
        client_info = get_client_info(request)

        rate_limit_logger.warning(
            "Rate limit exceeded",
            extra={
                "event_type": "rate_limit_exceeded",
                "method": client_info["method"],
                "path": client_info["path"],
                "correlation_id": client_info["correlation_id"],
            },
        )

        return _rate_limit_exceeded_handler(request, exc)
    raise exc


def add_general_exception_handler() -> Callable[
    [Request, Exception], Awaitable[JSONResponse]
]:
    """Create a general exception handler for unexpected errors."""
    general_logger = get_exception_logger("general")

    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle unexpected exceptions with proper logging."""
        client_info = get_client_info(request)

        general_logger.error(
            "Unexpected error occurred",
            extra={
                "event_type": "unexpected_error",
                "method": client_info["method"],
                "path": client_info["path"],
                "correlation_id": client_info["correlation_id"],
                "exception_type": type(exc).__name__,
            },
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error occurred.",
                "code": "internal_error",
                "correlation_id": client_info["correlation_id"],
            },
        )

    return general_exception_handler
