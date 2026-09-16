"""API endpoints for contact functionality."""

from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.core.limiter import limiter
from app.dependency.database import get_db_dep
from app.schema.requests.contact import ContactRequest
from app.service.contact import ContactService

router = APIRouter()
logger = get_logger(__name__)


@router.post("/send")
@limiter.limit("1/minute")  # Limit contact form submissions
async def send_contact_message(
    request: Request,
    body: ContactRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = get_db_dep,
) -> dict[str, str]:
    """Send a contact message to administrators.

    Args:
        request: The FastAPI request object
        body: The contact form data
        background_tasks: Background tasks manager
        db: Database session

    Returns:
        dict: Success message

    Raises:
        ElanoraError: If sending fails

    """
    try:
        # Detect language from Accept-Language header
        accept_language = request.headers.get("accept-language", "en")
        language = "fr" if accept_language.startswith("fr") else "en"

        # Send contact message to all administrators
        await ContactService.send_contact_message(
            db=db,
            email=body.email,
            request_type=body.request_type,
            message=body.message,
            background_tasks=background_tasks,
            language=language,
        )

        return {"message": "Contact message sent successfully"}

    except ElanoraError:
        raise
    except Exception as e:
        logger.error("Contact endpoint failed; error_type=%s", safe_exception_type(e))
        raise ElanoraError(ErrorCode.CONTACT_FAILED) from e
