"""Refuse passwords that appear in known data breaches.

The check uses the Have I Been Pwned "Pwned Passwords" range API with
k-anonymity: the server receives only the first five hexadecimal characters of
the password's SHA-1 hash and returns every breached hash that starts with
them, and the comparison happens here. Neither the password nor its full hash
leaves the installation. Responses are padded so their size does not reveal
the prefix either.

When the service cannot be reached, the check does not block the researcher:
the shipped list of common passwords in ``password_policy`` still applies, and
the failure is logged for the administrator.
"""

import hashlib
from typing import Literal

import httpx

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.core.settings import get_settings

logger = get_logger(__name__)

PREFIX_LENGTH = 5
USER_AGENT = "ELANORA password breach check"

BreachStatus = Literal["breached", "not_found", "unavailable"]


async def breach_status(
    password: str, *, client: httpx.AsyncClient | None = None
) -> BreachStatus:
    """Whether the password appears in a known breach, as far as can be told."""
    settings = get_settings()
    digest = hashlib.sha1(password.encode("utf-8"), usedforsecurity=False)
    sha1 = digest.hexdigest().upper()
    prefix, suffix = sha1[:PREFIX_LENGTH], sha1[PREFIX_LENGTH:]
    try:
        owns_client = client is None
        http = client or httpx.AsyncClient(
            timeout=settings.breach_check_timeout_seconds
        )
        try:
            response = await http.get(
                f"{settings.breach_check_api_url}{prefix}",
                headers={"Add-Padding": "true", "User-Agent": USER_AGENT},
            )
            response.raise_for_status()
        finally:
            if owns_client:
                await http.aclose()
    except httpx.HTTPError as error:
        logger.warning(
            "Password breach check unavailable; error_type=%s",
            safe_exception_type(error),
        )
        return "unavailable"

    for line in response.text.splitlines():
        candidate, _, count = line.strip().partition(":")
        # Padding entries carry a count of zero.
        if candidate.upper() == suffix and count.strip() not in {"", "0"}:
            return "breached"
    return "not_found"


async def refuse_breached_password(
    password: str, *, client: httpx.AsyncClient | None = None
) -> None:
    """Raise ``password_breached`` for a password found in a known breach."""
    if not get_settings().password_breach_check:
        return
    if await breach_status(password, client=client) == "breached":
        raise ElanoraError(ErrorCode.PASSWORD_BREACHED)
