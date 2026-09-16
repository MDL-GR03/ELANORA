"""Transactional email renders the shipped templates, safely."""

import re
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.schema.requests.contact import RequestType
from app.service import contact, email
from app.service.contact import ContactService
from app.service.email import EmailService, render_template

HOSTILE = '<a href="https://evil.example">click</a>'

SENDS = {
    "send_password_reset_verification_email": {
        "email": "r@example.org",
        "username": HOSTILE,
        "code": "123456",
    },
    "send_email_verification_code": {
        "email": "r@example.org",
        "username": HOSTILE,
        "code": "123456",
    },
    "send_invitation_email": {
        "email": "r@example.org",
        "invitation_code": "CODE",
        "sender_name": HOSTILE,
        "project_name": "Corpus",
        "custom_message": HOSTILE,
    },
    "send_existing_user_invitation_email": {
        "email": "r@example.org",
        "invitation_id": 7,
        "sender_name": HOSTILE,
        "project_name": "Corpus",
        "custom_message": HOSTILE,
    },
    "send_role_change_email": {
        "email": "r@example.org",
        "username": HOSTILE,
        "project_name": "Corpus",
        "new_role": "write",
        "admin_name": "Admin",
    },
}


@pytest.fixture
def sent(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    capture = AsyncMock()
    monkeypatch.setattr(EmailService, "send_html", capture)
    return capture


@pytest.mark.asyncio
@pytest.mark.parametrize("language", ["en", "fr"])
@pytest.mark.parametrize("method", sorted(SENDS))
async def test_every_email_renders_its_designed_template(
    sent: AsyncMock, method: str, language: str
) -> None:
    assert await getattr(EmailService(), method)(**SENDS[method], language=language)

    recipient, subject, body = sent.await_args.args
    assert recipient == "r@example.org"
    assert subject.startswith("ELANORA")
    assert "<!DOCTYPE" in body or "<html" in body
    assert not re.search(r"\{[a-z_]+\}", body), "a placeholder was left unfilled"
    assert "{{" not in body, "doubled braces reach the recipient as broken CSS"


@pytest.mark.asyncio
@pytest.mark.parametrize("method", sorted(SENDS))
async def test_text_from_people_cannot_become_markup(
    sent: AsyncMock, method: str
) -> None:
    await getattr(EmailService(), method)(**SENDS[method])

    body = sent.await_args.args[2]
    assert HOSTILE not in body
    if "evil.example" in body:
        assert "&lt;a href=&quot;https://evil.example&quot;&gt;" in body


@pytest.mark.asyncio
async def test_an_existing_account_gets_the_accept_and_reject_links(
    sent: AsyncMock,
) -> None:
    await EmailService().send_existing_user_invitation_email(
        **SENDS["send_existing_user_invitation_email"]
    )

    body = sent.await_args.args[2]
    assert "/invitation/accept/7" in body
    assert "/invitation/reject/7" in body
    assert "@media screen and (min-width: 480px) {" in body


def test_a_template_placeholder_without_a_value_refuses_to_render() -> None:
    with pytest.raises(KeyError):
        render_template("role_change", "en", {"username": "someone"})


def test_an_unknown_language_falls_back_to_english() -> None:
    body = render_template(
        "email_verification",
        "ja",
        {"username": "u", "code": "1", "year": 2026, "contact_url": "x"},
    )
    assert 'lang="fr"' not in body


@pytest.mark.asyncio
async def test_a_failed_role_change_email_is_reported_not_raised(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        EmailService, "send_html", AsyncMock(side_effect=ConnectionError())
    )
    assert (
        await EmailService().send_role_change_email(**SENDS["send_role_change_email"])
        is False
    )


@pytest.mark.asyncio
async def test_a_contact_message_reaches_administrators_escaped(
    sent: AsyncMock,
) -> None:
    await ContactService._send_contact_emails(
        admin_emails=["a@example.org", "b@example.org"],
        sender_email="visitor@example.org",
        request_type=RequestType.BUG_REPORT,
        message=HOSTILE,
        language="fr",
    )

    assert [call.args[0] for call in sent.await_args_list] == [
        "a@example.org",
        "b@example.org",
    ]
    subject, body = sent.await_args.args[1:]
    assert subject == "ELANORA Formulaire de Contact - Signalement de Bug"
    assert HOSTILE not in body


@pytest.mark.asyncio
async def test_a_contact_message_goes_nowhere_without_an_administrator(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(contact, "get_admin_emails", AsyncMock(return_value=[]))
    tasks = MagicMock()

    await ContactService.send_contact_message(
        AsyncMock(),
        "visitor@example.org",
        RequestType.OTHER,
        "hello",
        tasks,
    )

    tasks.add_task.assert_not_called()


def test_email_module_keeps_no_password_hashing() -> None:
    assert not hasattr(email, "pwd_context")
