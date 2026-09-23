"""Transactional email: rendering the shipped templates and sending them."""

import datetime
import html
import re
from collections.abc import Mapping
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import NameEmail, SecretStr

from app.core import config
from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type

logger = get_logger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "template" / "emails"

# Only a lowercase name in single braces is a placeholder, so the CSS inside a
# template ("{ display: table }") is left alone.
PLACEHOLDER = re.compile(r"\{([a-z_]+)\}")


class SafeHtml(str):
    """Markup this module built itself, inserted into a template unescaped."""


def email_language(language: str | None) -> str:
    """The template language for a requested language; English by default."""
    return "fr" if (language or "").lower() == "fr" else "en"


def render_template(name: str, language: str, fields: Mapping[str, object]) -> str:
    """Fill a shipped template, escaping every value that is not ``SafeHtml``.

    Every value arrives from someone else: a researcher's name, an invitation
    message, a contact form. Escaping them keeps that text from becoming markup
    in the recipient's mail client. A placeholder the caller did not supply is a
    mismatch between template and code, and raises rather than sending an
    email with a hole in it.
    """
    path = TEMPLATES_DIR / f"{name}_{email_language(language)}.html"
    template = path.read_text(encoding="utf-8")

    def fill(match: re.Match[str]) -> str:
        value = fields[match.group(1)]
        return value if isinstance(value, SafeHtml) else html.escape(str(value))

    return PLACEHOLDER.sub(fill, template)


def personal_message_block(message: str | None, language: str) -> SafeHtml:
    """The inviter's own words, set apart from the invitation text."""
    if not message:
        return SafeHtml("")
    label = (
        "Message personnel :"
        if email_language(language) == "fr"
        else "Personal message:"
    )
    return SafeHtml(
        '<div style="background:#e8f0fe;border:1px solid #2563eb;'
        'border-radius:0.75rem;padding:1.5rem;margin:1.5rem 0;">'
        '<div style="font-size:1rem;color:#1d4ed8;font-weight:600;'
        f'margin-bottom:0.5rem;">{label}</div>'
        '<div style="font-size:0.95rem;color:#4b5563;line-height:1.6;">'
        f"{html.escape(message)}</div></div>"
    )


SUBJECTS = {
    "password_verification": {
        "en": "ELANORA - Password Verification",
        "fr": "ELANORA - Vérification de votre mot de passe",
    },
    "email_verification": {
        "en": "ELANORA - Email Address Verification",
        "fr": "ELANORA - Vérification de votre adresse email",
    },
    "invitation": {
        "en": "ELANORA - Invitation to join the platform",
        "fr": "ELANORA - Invitation à rejoindre la plateforme",
    },
    "existing_user_invitation": {
        "en": "ELANORA - Project Invitation",
        "fr": "ELANORA - Invitation à rejoindre un projet",
    },
    "role_change": {
        "en": "ELANORA - Role Updated in Project",
        "fr": "ELANORA - Rôle modifié dans le projet",
    },
}


def _common_fields() -> dict[str, object]:
    return {
        "year": datetime.datetime.now(datetime.UTC).year,
        "contact_url": f"{config.FRONTEND_HOST}/contact",
    }


class EmailService:
    """Sends the installation's transactional email."""

    def __init__(self) -> None:
        self.conf = ConnectionConfig(
            MAIL_USERNAME=config.MAIL_USERNAME,
            MAIL_PASSWORD=SecretStr(config.MAIL_PASSWORD),
            MAIL_FROM=config.MAIL_FROM,
            MAIL_PORT=config.MAIL_PORT,
            MAIL_SERVER=config.MAIL_SERVER,
            MAIL_STARTTLS=config.MAIL_STARTTLS,
            MAIL_SSL_TLS=config.MAIL_SSL_TLS,
            USE_CREDENTIALS=config.MAIL_USE_CREDENTIALS,
        )

    async def send_html(self, recipient: str, subject: str, body: str) -> None:
        """Send one HTML message."""
        await FastMail(self.conf).send_message(
            MessageSchema(
                subject=subject,
                recipients=[NameEmail(name=recipient, email=recipient)],
                body=body,
                subtype=MessageType.html,
            )
        )

    async def _send_template(
        self,
        recipient: str,
        name: str,
        language: str,
        fields: Mapping[str, object],
    ) -> bool:
        body = render_template(name, language, {**_common_fields(), **fields})
        subject = SUBJECTS[name][email_language(language)]
        try:
            await self.send_html(recipient, subject, body)
        except Exception as error:
            logger.error(
                "Failed to send an email; template=%s error_type=%s",
                name,
                safe_exception_type(error),
            )
            raise
        return True

    async def send_password_reset_verification_email(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        """Send the code that authorises a password reset."""
        return await self._send_template(
            email,
            "password_verification",
            language,
            {"username": username, "code": code},
        )

    async def send_email_verification_code(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        """Send the code that confirms an account's email address."""
        return await self._send_template(
            email,
            "email_verification",
            language,
            {"username": username, "code": code},
        )

    async def send_invitation_email(
        self,
        email: str,
        invitation_code: str,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        """Invite someone without an account to register."""
        project_info = ""
        if project_name:
            project_info = (
                f" pour le projet '{project_name}'"
                if email_language(language) == "fr"
                else f" for the project '{project_name}'"
            )
        return await self._send_template(
            email,
            "invitation",
            language,
            {
                "sender_name": sender_name,
                "project_info": project_info,
                "custom_message": personal_message_block(custom_message, language),
                "invitation_code": invitation_code,
                "register_url": (
                    f"{config.FRONTEND_HOST}/register?invitation={invitation_code}"
                ),
            },
        )

    async def send_existing_user_invitation_email(
        self,
        email: str,
        invitation_id: int,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        """Invite an existing account to a project, with accept and reject links."""
        return await self._send_template(
            email,
            "existing_user_invitation",
            language,
            {
                "sender_name": sender_name,
                "project_info": f" '{project_name}'" if project_name else "",
                "custom_message": personal_message_block(custom_message, language),
                "accept_url": f"{config.FRONTEND_HOST}/invitation/accept/{invitation_id}",
                "reject_url": f"{config.FRONTEND_HOST}/invitation/reject/{invitation_id}",
            },
        )

    async def send_role_change_email(
        self,
        email: str,
        username: str,
        project_name: str,
        new_role: str,
        admin_name: str,
        language: str = "en",
    ) -> bool:
        """Tell a member their role in a project changed.

        The change itself has already been saved, so a delivery failure is
        reported rather than raised.
        """
        try:
            return await self._send_template(
                email,
                "role_change",
                language,
                {
                    "username": username,
                    "project_name": project_name,
                    "new_role": new_role,
                    "admin_name": admin_name,
                    "project_url": f"{config.FRONTEND_HOST}/projects",
                },
            )
        except Exception:
            return False
