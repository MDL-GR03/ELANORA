import pytest
from pydantic import ValidationError

from app.schema.requests.setup import SetupInitializeRequest


def valid_setup() -> dict[str, str]:
    return {
        "instance_name": "Corpus Portal",
        "institution_name": "Research Institute",
        "contact_email": "contact@example.org",
        "domain": "example.org",
        "timezone": "Europe/Paris",
        "default_language": "en",
        "primary_color": "#123456",
        "secondary_color": "#0f766e",
        "accent_color": "#d97706",
        "admin_username": "owner",
        "admin_email": "owner@example.org",
        "admin_first_name": "Research",
        "admin_last_name": "Owner",
        "admin_affiliation": "Research Institute",
        "admin_department": "Corpus Lab",
        "password": "correct horse battery staple",
        "password_confirmation": "correct horse battery staple",
    }


def test_setup_rejects_mismatched_passwords() -> None:
    data = valid_setup()
    data["password_confirmation"] = "different secure password"  # noqa: S105
    with pytest.raises(ValidationError, match="password confirmation"):
        SetupInitializeRequest.model_validate(data)


def test_setup_rejects_non_hex_theme_color() -> None:
    data = valid_setup()
    data["primary_color"] = "blue"
    with pytest.raises(ValidationError, match="primary_color"):
        SetupInitializeRequest.model_validate(data)
