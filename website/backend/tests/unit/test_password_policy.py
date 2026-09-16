"""Every way of setting a password enforces the same policy."""

import pytest
from pydantic import ValidationError

from app.core.password_policy import password_policy_violations
from app.schema.requests.register_with_invitation import RegisterWithInvitationRequest
from app.schema.requests.user import ChangePasswordRequest, ResetPasswordRequest

ACCEPTABLE = "Analytical1!"


@pytest.mark.parametrize(
    ("password", "broken"),
    [
        ("Ab1!", "at least 8 characters"),
        ("analytical1!", "an uppercase letter"),
        ("ANALYTICAL1!", "a lowercase letter"),
        ("Analytical!!", "a number"),
        ("Analytical12", "a special character"),
        ("A1!" + "a" * 70, "at most 72 bytes"),
    ],
)
def test_each_rule_is_named_when_broken(password: str, broken: str) -> None:
    assert broken in password_policy_violations(password)


def test_an_underscore_counts_as_a_special_character() -> None:
    assert password_policy_violations("Analytical_1") == []


def test_accented_letters_count_against_the_byte_limit() -> None:
    assert "at most 72 bytes" in password_policy_violations("Aé1!" + "é" * 35)


def _register(password: str) -> RegisterWithInvitationRequest:
    return RegisterWithInvitationRequest(
        invitation_code="code",
        first_name="Ada",
        last_name="Lovelace",
        username="ada",
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
def test_the_api_refuses_a_weak_password_wherever_one_is_set(build) -> None:
    build(ACCEPTABLE)
    with pytest.raises(ValidationError, match="Password must contain"):
        build("password")
