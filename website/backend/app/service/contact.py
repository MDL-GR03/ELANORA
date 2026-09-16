"""Service for handling contact form submissions."""

import datetime

from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.user import get_admin_emails
from app.schema.requests.contact import RequestType
from app.service.email import EmailService, email_language, render_template

logger = get_logger(__name__)

REQUEST_TYPE_LABELS = {
    "en": {
        RequestType.BUG_REPORT: "Bug Report",
        RequestType.FEATURE_REQUEST: "Feature Request",
        RequestType.TECHNICAL_SUPPORT: "Technical Support",
        RequestType.ACCOUNT_ISSUE: "Account Issue",
        RequestType.GENERAL_INQUIRY: "General Inquiry",
        RequestType.OTHER: "Other",
    },
    "fr": {
        RequestType.BUG_REPORT: "Signalement de Bug",
        RequestType.FEATURE_REQUEST: "Demande de Fonctionnalité",
        RequestType.TECHNICAL_SUPPORT: "Support Technique",
        RequestType.ACCOUNT_ISSUE: "Problème de Compte",
        RequestType.GENERAL_INQUIRY: "Demande Générale",
        RequestType.OTHER: "Autre",
    },
}
SUBJECT_PREFIX = {"en": "ELANORA Contact Form", "fr": "ELANORA Formulaire de Contact"}


class ContactService:
    """Service for handling contact form submissions."""

    @staticmethod
    async def send_contact_message(
        db: AsyncSession,
        email: str,
        request_type: RequestType,
        message: str,
        background_tasks: BackgroundTasks,
        language: str = "en",
    ) -> None:
        """Send a contact message to all administrators.

        Args:
            db: Database session
            email: Email address of the sender
            request_type: Type of contact request
            message: Message content
            background_tasks: Background tasks manager
            language: Language for email template ("en" or "fr")

        Raises:
            Exception: If sending fails

        """
        # Get all admin email addresses
        admin_emails = await get_admin_emails(db)

        if not admin_emails:
            # Never send a visitor's message anywhere but this institution.
            logger.warning("No administrator emails found for contact message")
            return

        # Add background task to send emails
        background_tasks.add_task(
            ContactService._send_contact_emails,
            admin_emails=admin_emails,
            sender_email=email,
            request_type=request_type,
            message=message,
            language=language,
        )

        logger.info(
            f"Contact message queued for sending to {len(admin_emails)} administrators"
        )

    @staticmethod
    async def _send_contact_emails(
        admin_emails: list[str],
        sender_email: str,
        request_type: RequestType,
        message: str,
        language: str = "en",
    ) -> None:
        """Send contact emails to administrators (background task).

        Args:
            admin_emails: List of administrator email addresses
            sender_email: Email address of the sender
            request_type: Type of contact request
            message: Message content
            language: Language for email template ("en" or "fr")

        """
        language = email_language(language)
        request_label = REQUEST_TYPE_LABELS[language].get(
            request_type, request_type.value
        )
        now = datetime.datetime.now(datetime.UTC)
        body = render_template(
            "contact_admin",
            language,
            {
                "sender_email": sender_email,
                "request_type": request_label,
                "message": message,
                "date": now.strftime("%Y-%m-%d %H:%M:%S UTC"),
                "year": now.year,
            },
        )
        subject = f"{SUBJECT_PREFIX[language]} - {request_label}"

        email_service = EmailService()
        for admin_email in admin_emails:
            try:
                await email_service.send_html(admin_email, subject, body)
                logger.info("Contact message sent to an institution administrator")
            except Exception as e:
                logger.error(
                    "Failed to send a contact message; error_type=%s",
                    safe_exception_type(e),
                )
