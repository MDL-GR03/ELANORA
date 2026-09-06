"""Service for sending password verification emails."""

import datetime
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from passlib.context import CryptContext
from pydantic import SecretStr

from app.core import config

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# Email template paths
TEMPLATES_DIR = Path(__file__).parent.parent / "template" / "emails"
PASSWORD_VERIFICATION_TEMPLATE_EN = TEMPLATES_DIR / "password_verification_en.html"
PASSWORD_VERIFICATION_TEMPLATE_FR = TEMPLATES_DIR / "password_verification_fr.html"
EMAIL_VERIFICATION_TEMPLATE_EN = TEMPLATES_DIR / "email_verification_en.html"
EMAIL_VERIFICATION_TEMPLATE_FR = TEMPLATES_DIR / "email_verification_fr.html"
INVITATION_TEMPLATE_EN = TEMPLATES_DIR / "invitation_en.html"
INVITATION_TEMPLATE_FR = TEMPLATES_DIR / "invitation_fr.html"
EXISTING_USER_INVITATION_TEMPLATE_EN = (
    TEMPLATES_DIR / "existing_user_invitation_en.html"
)
EXISTING_USER_INVITATION_TEMPLATE_FR = (
    TEMPLATES_DIR / "existing_user_invitation_fr.html"
)
ROLE_CHANGE_TEMPLATE_EN = TEMPLATES_DIR / "role_change_en.html"
ROLE_CHANGE_TEMPLATE_FR = TEMPLATES_DIR / "role_change_fr.html"


class EmailService:
    """Service for sending password verification and reset emails."""

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

    @staticmethod
    def load_template(template_path: Path) -> str:
        """Load an email template from a file."""
        try:
            with open(template_path, encoding="utf-8") as file:
                return file.read()
        except FileNotFoundError as err:
            raise FileNotFoundError(
                f"Email template not found: {template_path}"
            ) from err

    async def send_password_reset_verification_email(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        """Send a password reset verification email.

        Args:
            email (str): The email address to send the verification code to
            username (str): The username to personalize the email
            code (str): The verification code
            language (str): The language for the email template ("en" or "fr")

        Returns:
            bool: True if the email was sent successfully, False otherwise

        """
        current_year = datetime.datetime.now().year
        contact_url = f"{config.FRONTEND_HOST}/contact"

        # Determine email template and subject based on language
        if language.lower() == "fr":
            subject = "ELANORA - Vérification de votre mot de passe"
            template_path = PASSWORD_VERIFICATION_TEMPLATE_FR
        else:
            subject = "ELANORA - Password Verification"
            template_path = PASSWORD_VERIFICATION_TEMPLATE_EN

        # Load and format the email template
        try:
            template = self.load_template(template_path)
            email_body = template.format(
                username=username,
                code=code,
                year=current_year,
                contact_url=contact_url,
            )
        except Exception as e:
            print(f"[EmailService] Failed to load or format template: {e}")
            # Fallback template in case of error
            if language.lower() == "en":
                email_body = f"""
                <html>
                  <body>
                    <h1>Password Verification</h1>
                    <p>Hello {username},</p>
                    <p>Your verification code is: {code}</p>
                    <p><a href=\"{contact_url}\">Click here to contact support</a></p>
                  </body>
                </html>
                """
            else:
                email_body = f"""
                <html>
                  <body>
                    <h1>Vérification de votre mot de passe</h1>
                    <p>Bonjour {username},</p>
                    <p>Votre code de vérification est : {code}</p>
                    <p><a href=\"{contact_url}\">Cliquez ici pour contacter le support</a></p>
                  </body>
                </html>
                """

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=email_body,
            subtype=MessageType.html,
        )

        try:
            fm = FastMail(self.conf)
            await fm.send_message(message)
            return True
        except Exception as e:
            print(
                f"[EmailService] Failed to send password reset verification email: {e}"
            )
            raise e

    async def send_invitation_email(
        self,
        email: str,
        invitation_code: str,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        """Send an invitation email with registration link.

        Args:
            email (str): The email address to send the invitation to
            invitation_code (str): The invitation code for registration link
            sender_name (str): The name of the person sending the invitation
            project_name (str): The name of the project (optional)
            custom_message (str): Custom message from the sender (optional)
            language (str): The language for the email ("en" or "fr")

        Returns:
            bool: True if the email was sent successfully, False otherwise

        """
        current_year = datetime.datetime.now().year
        contact_url = f"{config.FRONTEND_HOST}/contact"
        register_url = f"{config.FRONTEND_HOST}/register?invitation={invitation_code}"

        # Determine email template and subject based on language
        if language.lower() == "fr":
            subject = "ELANORA - Invitation à rejoindre la plateforme"
            template_path = INVITATION_TEMPLATE_FR
            project_info = f" pour le projet '{project_name}'" if project_name else ""
        else:
            subject = "ELANORA - Invitation to join the platform"
            template_path = INVITATION_TEMPLATE_EN
            project_info = f" for the project '{project_name}'" if project_name else ""

        # Format custom message if provided
        formatted_custom_message = ""
        if custom_message:
            if language.lower() == "fr":
                formatted_custom_message = f"""
                <div style="background:#e8f0fe;border:1px solid #2563eb;border-radius:0.75rem;padding:1.5rem;margin:1.5rem 0;">
                    <div style="font-size:1rem;color:#1d4ed8;font-weight:600;margin-bottom:0.5rem;">Message personnel :</div>
                    <div style="font-size:0.95rem;color:#4b5563;line-height:1.6;">{custom_message}</div>
                </div>
                """
            else:
                formatted_custom_message = f"""
                <div style="background:#e8f0fe;border:1px solid #2563eb;border-radius:0.75rem;padding:1.5rem;margin:1.5rem 0;">
                    <div style="font-size:1rem;color:#1d4ed8;font-weight:600;margin-bottom:0.5rem;">Personal message:</div>
                    <div style="font-size:0.95rem;color:#4b5563;line-height:1.6;">{custom_message}</div>
                </div>
                """

        # Load and format the email template
        try:
            template = self.load_template(template_path)
            email_body = template.format(
                sender_name=sender_name,
                project_info=project_info,
                custom_message=formatted_custom_message,
                invitation_code=invitation_code,
                register_url=register_url,
                year=current_year,
                contact_url=contact_url,
            )
        except Exception as e:
            print(f"[EmailService] Failed to load or format invitation template: {e}")
            # Fallback to simple template
            if language.lower() == "fr":
                fallback_subject = "ELANORA - Invitation à rejoindre la plateforme"
                fallback_intro = (
                    f"{sender_name} vous invite à rejoindre ELANORA{project_info}."
                )
                fallback_cta = "Créer mon compte"
                fallback_footer = "Cette invitation expirera dans 7 jours."
            else:
                fallback_subject = "ELANORA - Invitation to join the platform"
                fallback_intro = (
                    f"{sender_name} has invited you to join ELANORA{project_info}."
                )
                fallback_cta = "Create my account"
                fallback_footer = "This invitation will expire in 7 days."

            email_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h1 style="color: #2563eb;">ELANORA</h1>
                  <h2>Invitation</h2>
                  <p>{fallback_intro}</p>
                  {formatted_custom_message if custom_message else ""}
                  <div style="background: #f0f4ff; padding: 20px; text-align: center; margin: 20px 0; border-radius: 8px;">
                    <p><strong>Invitation Code:</strong></p>
                    <div style="font-size: 24px; font-weight: bold; color: #2563eb; font-family: monospace; margin: 10px 0;">{invitation_code}</div>
                  </div>
                  <p style="text-align: center;">
                    <a href="{register_url}" style="background: #2563eb; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block;">{fallback_cta}</a>
                  </p>
                  <p style="font-size: 14px; color: #666;">{fallback_footer}</p>
                  <p style="font-size: 12px; color: #999;">© {current_year} ELANORA. All rights reserved.</p>
                </div>
              </body>
            </html>
            """
            subject = fallback_subject

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=email_body,
            subtype=MessageType.html,
        )

        try:
            fm = FastMail(self.conf)
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send invitation email: {e}")
            raise e

    async def send_email_verification_code(
        self, email: str, username: str, code: str, language: str = "en"
    ) -> bool:
        """Send an email verification code to verify account.

        Args:
            email (str): The email address to send the verification code to
            username (str): The username to personalize the email
            code (str): The verification code
            language (str): The language for the email template ("en" or "fr")

        Returns:
            bool: True if the email was sent successfully, False otherwise

        """
        current_year = datetime.datetime.now().year
        contact_url = f"{config.FRONTEND_HOST}/contact"

        # Determine email template and subject based on language
        if language.lower() == "fr":
            subject = "ELANORA - Vérification de votre adresse email"
            template_path = EMAIL_VERIFICATION_TEMPLATE_FR
        else:
            subject = "ELANORA - Email Address Verification"
            template_path = EMAIL_VERIFICATION_TEMPLATE_EN

        # Load and format the email template
        try:
            template = self.load_template(template_path)
            email_body = template.format(
                username=username,
                code=code,
                year=current_year,
                contact_url=contact_url,
            )
        except Exception as e:
            print(f"[EmailService] Failed to load or format template: {e}")
            # Fallback template in case of error
            if language.lower() == "en":
                email_body = f"""
                <html>
                  <body>
                    <h1>Email Verification</h1>
                    <p>Hello {username},</p>
                    <p>Please verify your email address by entering this code:</p>
                    <div style="font-size: 24px; font-weight: bold; color: #2563eb; font-family: monospace; margin: 20px 0; text-align: center; padding: 20px; background: #f0f4ff; border-radius: 8px;">{code}</div>
                    <p>This code will expire in 10 minutes.</p>
                    <p><a href=\"{contact_url}\">Click here to contact support</a></p>
                  </body>
                </html>
                """
            else:
                email_body = f"""
                <html>
                  <body>
                    <h1>Vérification de votre adresse email</h1>
                    <p>Bonjour {username},</p>
                    <p>Veuillez vérifier votre adresse email en saisissant ce code :</p>
                    <div style="font-size: 24px; font-weight: bold; color: #2563eb; font-family: monospace; margin: 20px 0; text-align: center; padding: 20px; background: #f0f4ff; border-radius: 8px;">{code}</div>
                    <p>Ce code expirera dans 10 minutes.</p>
                    <p><a href=\"{contact_url}\">Cliquez ici pour contacter le support</a></p>
                  </body>
                </html>
                """

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=email_body,
            subtype=MessageType.html,
        )

        try:
            fm = FastMail(self.conf)
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send email verification code: {e}")
            raise e

    async def send_existing_user_invitation_email(
        self,
        email: str,
        invitation_id: int,
        sender_name: str,
        project_name: str | None = None,
        custom_message: str | None = None,
        language: str = "en",
    ) -> bool:
        """Send an invitation email to an existing user with accept/reject buttons.

        Args:
            email (str): The email address to send the invitation to
            invitation_id (int): The invitation ID for accept/reject links
            sender_name (str): The name of the person sending the invitation
            project_name (str): The name of the project (optional)
            custom_message (str): Custom message from the sender (optional)
            language (str): The language for the email ("en" or "fr")

        Returns:
            bool: True if the email was sent successfully, False otherwise

        """
        current_year = datetime.datetime.now().year
        contact_url = f"{config.FRONTEND_HOST}/contact"
        accept_url = f"{config.FRONTEND_HOST}/invitation/accept/{invitation_id}"
        reject_url = f"{config.FRONTEND_HOST}/invitation/reject/{invitation_id}"

        # Determine email template and subject based on language
        if language.lower() == "fr":
            subject = "ELANORA - Invitation à rejoindre un projet"
            template_path = EXISTING_USER_INVITATION_TEMPLATE_FR
            project_info = f" '{project_name}'" if project_name else ""
        else:
            subject = "ELANORA - Project Invitation"
            template_path = EXISTING_USER_INVITATION_TEMPLATE_EN
            project_info = f" '{project_name}'" if project_name else ""

        # Format custom message if provided
        formatted_custom_message = ""
        if custom_message:
            if language.lower() == "fr":
                formatted_custom_message = f"""
                <div style="background:#e8f0fe;border:1px solid #2563eb;border-radius:0.75rem;padding:1.5rem;margin:1.5rem 0;">
                    <div style="font-size:1rem;color:#1d4ed8;font-weight:600;margin-bottom:0.5rem;">Message personnel :</div>
                    <div style="font-size:0.95rem;color:#4b5563;line-height:1.6;">{custom_message}</div>
                </div>
                """
            else:
                formatted_custom_message = f"""
                <div style="background:#e8f0fe;border:1px solid #2563eb;border-radius:0.75rem;padding:1.5rem;margin:1.5rem 0;">
                    <div style="font-size:1rem;color:#1d4ed8;font-weight:600;margin-bottom:0.5rem;">Personal message:</div>
                    <div style="font-size:0.95rem;color:#4b5563;line-height:1.6;">{custom_message}</div>
                </div>
                """

        # Load and format the email template
        try:
            template = self.load_template(template_path)
            email_body = template.format(
                sender_name=sender_name,
                project_info=project_info,
                custom_message=formatted_custom_message,
                accept_url=accept_url,
                reject_url=reject_url,
                year=current_year,
                contact_url=contact_url,
            )
        except Exception as e:
            print(
                f"[EmailService] Failed to load or format existing user invitation template: {e}"
            )
            # Fallback to simple template
            if language.lower() == "fr":
                fallback_subject = "ELANORA - Invitation à rejoindre un projet"
                fallback_intro = f"{sender_name} vous invite à rejoindre le projet{project_info} sur ELANORA."
                fallback_accept = "Accepter"
                fallback_reject = "Refuser"
                fallback_footer = "Cette invitation expirera dans 7 jours."
            else:
                fallback_subject = "ELANORA - Project Invitation"
                fallback_intro = f"{sender_name} has invited you to join the project{project_info} on ELANORA."
                fallback_accept = "Accept"
                fallback_reject = "Reject"
                fallback_footer = "This invitation will expire in 7 days."

            email_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                  <h1 style="color: #2563eb;">ELANORA</h1>
                  <h2>Project Invitation</h2>
                  <p>{fallback_intro}</p>
                  {formatted_custom_message if custom_message else ""}
                  <div style="text-align: center; margin: 30px 0;">
                    <a href="{accept_url}" style="background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 0 10px;">{fallback_accept}</a>
                    <a href="{reject_url}" style="background: #ef4444; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 0 10px;">{fallback_reject}</a>
                  </div>
                  <p style="font-size: 14px; color: #666;">{fallback_footer}</p>
                  <p style="font-size: 12px; color: #999;">© {current_year} ELANORA. All rights reserved.</p>
                </div>
              </body>
            </html>
            """
            subject = fallback_subject

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=email_body,
            subtype=MessageType.html,
        )

        try:
            fm = FastMail(self.conf)
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send existing user invitation email: {e}")
            raise e

    async def send_role_change_email(
        self,
        email: str,
        username: str,
        project_name: str,
        new_role: str,
        admin_name: str,
        language: str = "en",
    ) -> bool:
        """Send a role change notification email.

        Args:
            email (str): The email address to send the notification to
            username (str): The username of the user whose role changed
            project_name (str): The name of the project
            new_role (str): The new role assigned to the user
            admin_name (str): The name of the admin who made the change
            language (str): The language for the email template ("en" or "fr")

        Returns:
            bool: True if the email was sent successfully, False otherwise

        """
        current_year = datetime.datetime.now().year
        contact_url = f"{config.FRONTEND_HOST}/contact"
        project_url = f"{config.FRONTEND_HOST}/projects"

        # Determine email template and subject based on language
        if language.lower() == "fr":
            subject = "ELANORA - Rôle modifié dans le projet"
            template_path = ROLE_CHANGE_TEMPLATE_FR
            fallback_subject = "ELANORA - Rôle modifié dans le projet"
        else:
            subject = "ELANORA - Role Updated in Project"
            template_path = ROLE_CHANGE_TEMPLATE_EN
            fallback_subject = "ELANORA - Role Updated in Project"

        # Load and format the email template
        try:
            template = self.load_template(template_path)
            email_body = template.format(
                username=username,
                project_name=project_name,
                new_role=new_role,
                admin_name=admin_name,
                project_url=project_url,
                contact_url=contact_url,
                year=current_year,
            )
        except Exception as e:
            print(f"[EmailService] Failed to load or format role change template: {e}")
            # Fallback template in case of error
            if language.lower() == "fr":
                email_body = f"""
                <html>
                  <body>
                    <h1>Rôle modifié</h1>
                    <p>Bonjour {username},</p>
                    <p>Votre rôle dans le projet "{project_name}" a été modifié à "{new_role}" par {admin_name}.</p>
                    <p>Cordialement,<br>L'équipe ELANORA</p>
                    <p style="font-size: 12px; color: #999;">© {current_year} ELANORA. Tous droits réservés.</p>
                  </body>
                </html>
                """
            else:
                email_body = f"""
                <html>
                  <body>
                    <h1>Role Updated</h1>
                    <p>Hello {username},</p>
                    <p>Your role in project "{project_name}" has been updated to "{new_role}" by {admin_name}.</p>
                    <p>Best regards,<br>The ELANORA Team</p>
                    <p style="font-size: 12px; color: #999;">© {current_year} ELANORA. All rights reserved.</p>
                  </body>
                </html>
                """
            subject = fallback_subject

        message = MessageSchema(
            subject=subject,
            recipients=[email],
            body=email_body,
            subtype=MessageType.html,
        )

        try:
            fm = FastMail(self.conf)
            await fm.send_message(message)
            return True
        except Exception as e:
            print(f"[EmailService] Failed to send role change email: {e}")
            return False
