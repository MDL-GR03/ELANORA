"""The rules a researcher's chosen password must satisfy.

The interface shows the same five rules while the password is typed; this is
where they are enforced, so an account created or changed through the API
directly cannot skip them. Existing passwords are not re-checked at sign-in.
"""

import re
from typing import Annotated

from pydantic import AfterValidator

PASSWORD_MINIMUM_LENGTH = 8
# bcrypt ignores everything after 72 bytes, so a longer password would appear
# to be accepted while only its beginning protected the account.
PASSWORD_MAXIMUM_BYTES = 72

_RULES = (
    (re.compile(r"[a-z]"), "a lowercase letter"),
    (re.compile(r"[A-Z]"), "an uppercase letter"),
    (re.compile(r"\d"), "a number"),
    (re.compile(r"[^A-Za-z0-9]"), "a special character"),
)


def password_policy_violations(password: str) -> list[str]:
    """Describe every rule the password breaks; empty when it is acceptable."""
    violations = []
    if len(password) < PASSWORD_MINIMUM_LENGTH:
        violations.append(f"at least {PASSWORD_MINIMUM_LENGTH} characters")
    if len(password.encode("utf-8")) > PASSWORD_MAXIMUM_BYTES:
        violations.append(f"at most {PASSWORD_MAXIMUM_BYTES} bytes")
    violations.extend(
        description for pattern, description in _RULES if not pattern.search(password)
    )
    return violations


def _enforce(password: str) -> str:
    violations = password_policy_violations(password)
    if violations:
        raise ValueError("Password must contain " + ", ".join(violations))
    return password


NewPassword = Annotated[str, AfterValidator(_enforce)]
"""A password being set, which must satisfy the policy."""
