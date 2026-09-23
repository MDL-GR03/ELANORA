"""The rules a researcher's chosen password must satisfy.

The policy follows NIST SP 800-63B revision 4 for a password that is the only
authentication factor: a minimum length, no composition rules, and a refusal of
passwords that are known to be common, trivially repetitive, or built from the
account's own details. Existing passwords are not re-checked at sign-in.

A refusal carries a stable error type (``password_too_short`` and so on) so the
interface can explain it in the researcher's language.
"""

import re
from collections.abc import Iterable
from functools import cache
from itertools import pairwise
from pathlib import Path
from typing import Annotated, cast

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError

PASSWORD_MINIMUM_LENGTH = 15
# bcrypt ignores everything after 72 bytes, so a longer password would appear
# to be accepted while only its beginning protected the account.
PASSWORD_MAXIMUM_BYTES = 72
# Words that belong to the service itself, never a secret.
SERVICE_WORDS = ("elanora", "elan", "password")
MINIMUM_CONTEXT_WORD_LENGTH = 4

COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")

MESSAGES = {
    "too_short": f"Password must be at least {PASSWORD_MINIMUM_LENGTH} characters",
    "too_long": f"Password must be at most {PASSWORD_MAXIMUM_BYTES} bytes",
    "common": "Password is too common",
    "repetitive": "Password is a repeated or sequential pattern",
    "personal": "Password must not be built from the account's own details",
}


@cache
def common_passwords() -> frozenset[str]:
    """The shipped list of passwords known from breaches."""
    lines = COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(line for line in lines if line and not line.startswith("#"))


def _is_repetitive(password: str) -> bool:
    lowered = password.lower()
    # One short unit repeated to fill the length: "abcabcabcabcabc".
    if re.fullmatch(r"(.{1,4}?)\1+", lowered):
        return True
    # A run of consecutive characters: "123456789012345", "abcdefghijklmno".
    steps = {ord(b) - ord(a) for a, b in pairwise(lowered)}
    return len(steps) == 1 and steps <= {1, -1}


def _context_words(context: Iterable[str | None]) -> set[str]:
    words: set[str] = set(SERVICE_WORDS)
    for value in context:
        if not value:
            continue
        for part in re.split(r"[^a-z0-9]+", value.lower()):
            if len(part) >= MINIMUM_CONTEXT_WORD_LENGTH:
                words.add(part)
    return words


def password_policy_violation(
    password: str, context: Iterable[str | None] = ()
) -> str | None:
    """The first rule the password breaks, as an error code; None when acceptable.

    ``context`` holds the account's own details (username, email address,
    names), which must not make up the password.
    """
    if len(password) < PASSWORD_MINIMUM_LENGTH:
        return "too_short"
    if len(password.encode("utf-8")) > PASSWORD_MAXIMUM_BYTES:
        return "too_long"
    lowered = password.lower()
    if lowered in common_passwords():
        return "common"
    if _is_repetitive(password):
        return "repetitive"
    remainder = lowered
    for word in sorted(_context_words(context), key=len, reverse=True):
        remainder = remainder.replace(word, "")
    # A password that is mostly the account's own details, or the service's
    # name, is guessable by anyone who knows whose account it is.
    if len(lowered) - len(remainder) >= len(lowered) / 2:
        return "personal"
    return None


def password_policy_error(code: str) -> PydanticCustomError:
    """The validation error reported for a broken rule."""
    error_type = cast("str", f"password_{code}")
    return PydanticCustomError(error_type, MESSAGES[code])


def enforce_password_policy(password: str, context: Iterable[str | None] = ()) -> str:
    """Raise the policy error for a refused password, otherwise return it."""
    code = password_policy_violation(password, context)
    if code:
        raise password_policy_error(code)
    return password


NewPassword = Annotated[str, AfterValidator(enforce_password_policy)]
"""A password being set, checked for everything that needs no account details."""
