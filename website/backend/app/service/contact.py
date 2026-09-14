"""Service for handling contact form submissions."""

import datetime
from pathlib import Path

from fastapi import BackgroundTasks
from fastapi_mail import FastMail, MessageSchema, MessageType
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.user import get_admin_emails
from app.schema.requests.contact import RequestType
from app.service.email import EmailService

logger = get_logger(__name__)

# Email template paths
TEMPLATES_DIR = Path(__file__).parent.parent / "template" / "emails"
CONTACT_ADMIN_TEMPLATE_EN = TEMPLATES_DIR / "contact_admin_en.html"
CONTACT_ADMIN_TEMPLATE_FR = TEMPLATES_DIR / "contact_admin_fr.html"


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
            logger.warning("No administrator emails found for contact message")
            admin_emails = ["admin@example.com"]  # Fallback

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
        try:
            email_service = EmailService()
            current_year = datetime.datetime.now().year

            # Map request types to human-readable labels (bilingual)
            if language.lower() == "fr":
                request_type_labels = {
                    RequestType.BUG_REPORT: "Signalement de Bug",
                    RequestType.FEATURE_REQUEST: "Demande de Fonctionnalité",
                    RequestType.TECHNICAL_SUPPORT: "Support Technique",
                    RequestType.ACCOUNT_ISSUE: "Problème de Compte",
                    RequestType.GENERAL_INQUIRY: "Demande Générale",
                    RequestType.OTHER: "Autre",
                }
                subject = f"ELANORA Formulaire de Contact - {request_type_labels.get(request_type, request_type.value)}"
                template_path = CONTACT_ADMIN_TEMPLATE_FR
            else:
                request_type_labels = {
                    RequestType.BUG_REPORT: "Bug Report",
                    RequestType.FEATURE_REQUEST: "Feature Request",
                    RequestType.TECHNICAL_SUPPORT: "Technical Support",
                    RequestType.ACCOUNT_ISSUE: "Account Issue",
                    RequestType.GENERAL_INQUIRY: "General Inquiry",
                    RequestType.OTHER: "Other",
                }
                subject = f"ELANORA Contact Form - {request_type_labels.get(request_type, request_type.value)}"
                template_path = CONTACT_ADMIN_TEMPLATE_EN

            request_label = request_type_labels.get(request_type, request_type.value)

            # Try to load template, fall back to simple HTML if not found
            try:
                template = email_service.load_template(template_path)
                email_body = template.format(
                    sender_email=sender_email,
                    request_type=request_label,
                    message=message,
                    date=datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"),
                    year=current_year,
                )
            except FileNotFoundError:
                # Fallback template
                email_body = f"""
                <html>
                <head>
                    <meta charset="UTF-8">
                    <title>Contact Form Submission</title>
                </head>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h1 style="color: #2563eb;">ELANORA Contact Form</h1>

                        <div style="background-color: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h2 style="margin-top: 0;">New Contact Message</h2>
                            <p><strong>From:</strong> {sender_email}</p>
                            <p><strong>Request Type:</strong> {request_label}</p>
                            <p><strong>Date:</strong> {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}</p>
                        </div>

                        <div style="background-color: #ffffff; padding: 20px; border: 1px solid #e2e8f0; border-radius: 8px;">
                            <h3 style="margin-top: 0;">Message:</h3>
                            <p style="white-space: pre-wrap;">{message}</p>
                        </div>

                        <div style="margin-top: 30px; padding-top: 20px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #64748b;">
                            <p>This message was sent through the ELANORA contact form.</p>
                            <p>© {current_year} ELANORA Platform</p>
                        </div>
                    </div>
                </body>
                </html>
                """

            # Send email to all administrators
            for admin_email in admin_emails:
                try:
                    message_schema = MessageSchema(
                        subject=subject,
                        recipients=[admin_email],
                        body=email_body,
                        subtype=MessageType.html,
                    )

                    fm = FastMail(email_service.conf)
                    await fm.send_message(message_schema)

                    logger.info("Contact message sent to an institution administrator")

                except Exception as e:
                    logger.error(
                        "Failed to send a contact message; error_type=%s",
                        safe_exception_type(e),
                    )

        except Exception as e:
            logger.error(
                "Failed to send contact messages; error_type=%s",
                safe_exception_type(e),
            )
            raise
