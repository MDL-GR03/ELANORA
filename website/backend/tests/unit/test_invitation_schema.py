"""Validation rules for project invitations."""

import pytest
from pydantic import ValidationError

from app.schema.requests.invitation import InvitationSendRequest


def test_invitation_request_normalizes_email_and_language() -> None:
    request = InvitationSendRequest(
        receiver_email="Researcher@Example.ORG",
        project_name="Corpus",
        language=" FR ",
    )

    assert request.receiver_email == "researcher@example.org"
    assert request.language == "fr"


@pytest.mark.parametrize("expires_in_days", [0, 31])
def test_invitation_expiry_is_bounded(expires_in_days: int) -> None:
    with pytest.raises(ValidationError):
        InvitationSendRequest(
            receiver_email="researcher@example.org",
            project_name="Corpus",
            expires_in_days=expires_in_days,
        )


def test_invitation_language_requires_an_available_template() -> None:
    with pytest.raises(ValidationError):
        InvitationSendRequest(
            receiver_email="researcher@example.org",
            project_name="Corpus",
            language="de",
        )
