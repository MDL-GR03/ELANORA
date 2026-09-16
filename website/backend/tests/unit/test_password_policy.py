"""Every way of setting a password enforces the same NIST-style policy."""

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.password_policy import (
    PASSWORD_MINIMUM_LENGTH,
    common_passwords,
    password_policy_violation,
)
from app.schema.requests.register_with_invitation import RegisterWithInvitationRequest
from app.schema.requests.user import ChangePasswordRequest, ResetPasswordRequest

ACCEPTABLE = "tidal marsh 7 lanterns"


@pytest.mark.parametrize(
    ("password", "code"),
    [
        ("short phrase", "too_short"),
        ("a" * 60 + "é" * 7, "too_long"),
        ("aaaaaaaaaaaaaaaaaaaa", "repetitive"),
        ("abcabcabcabcabcabc", "repetitive"),
        ("zyxwvutsrqponmlk", "repetitive"),
        ("abcdefghijklmnop", "repetitive"),
        ("elanora-elanora-2026", "personal"),
    ],
)
def test_each_rule_names_its_refusal(password: str, code: str) -> None:
    assert password_policy_violation(password) == code


def test_a_long_password_needs_no_symbols_digits_or_capitals() -> None:
    assert password_policy_violation("the quiet river bends west") is None


def test_passwords_known_from_breaches_are_refused_whatever_their_case() -> None:
    known = next(iter(common_passwords()))
    assert len(known) >= PASSWORD_MINIMUM_LENGTH
    assert password_policy_violation(known.upper()) in {"common", "repetitive"}
    assert password_policy_violation(known) in {"common", "repetitive"}


def test_the_list_ignores_its_own_header() -> None:
    assert not any(entry.startswith("#") for entry in common_passwords())


def test_a_password_made_of_the_account_details_is_refused() -> None:
    context = ("ada_lovelace", "ada.lovelace@example.org", "Ada", "Lovelace")
    assert password_policy_violation("lovelace.lovelace", context) == "personal"
    assert password_policy_violation(ACCEPTABLE, context) is None


def _register(password: str) -> RegisterWithInvitationRequest:
    return RegisterWithInvitationRequest(
        invitation_code="code",
        first_name="Ada",
        last_name="Lovelace",
        username="ada_lovelace",
        email="ada@example.org",
        password=password,
        affiliation="Institute",
        department="Linguistics",
    )


@pytest.mark.parametrize(
    "build",
    [
        _register,
        lambda password: ResetPasswordRequest(
            email="ada@example.org", code="123456", new_password=password
        ),
        lambda password: ChangePasswordRequest(
            current_password="anything",  # noqa: S106 - inert test value
            new_password=password,
        ),
    ],
    ids=["registration", "reset", "change"],
)
def test_the_api_refuses_a_short_password_wherever_one_is_set(build) -> None:
    build(ACCEPTABLE)
    with pytest.raises(ValidationError) as caught:
        build("Sh0rt!")
    assert caught.value.errors()[0]["type"] == "password_too_short"


def test_registration_refuses_the_researchers_own_name() -> None:
    with pytest.raises(ValidationError) as caught:
        _register("LovelaceLovelace")
    assert caught.value.errors()[0]["type"] == "password_personal"


@pytest.mark.asyncio
async def test_changing_a_password_refuses_the_researchers_own_name() -> None:
    from types import SimpleNamespace  # noqa: PLC0415
    from unittest.mock import AsyncMock  # noqa: PLC0415

    from app.api.v1 import user as user_api  # noqa: PLC0415

    user = SimpleNamespace(
        username="ada_lovelace",
        email="ada@example.org",
        first_name="Ada",
        last_name="Lovelace",
    )
    with pytest.raises(HTTPException) as caught:
        await user_api.change_user_password(
            ChangePasswordRequest(
                current_password="anything",  # noqa: S106 - inert test value
                new_password="lovelace-lovelace",  # noqa: S106 - inert test value
            ),
            user,
            AsyncMock(),
        )
    assert caught.value.status_code == 400
    assert caught.value.detail[0]["type"] == "password_personal"
