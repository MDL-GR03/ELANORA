"""New passwords are checked against known breaches without revealing them."""

import hashlib
from types import SimpleNamespace

import httpx
import pytest

from app.core import breached_passwords
from app.core.errors import ElanoraError, ErrorCode

PASSWORD = "tidal marsh 7 lanterns"  # noqa: S105 - inert test value
SHA1 = hashlib.sha1(PASSWORD.encode(), usedforsecurity=False).hexdigest().upper()


@pytest.fixture(autouse=True)
def enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        breached_passwords,
        "get_settings",
        lambda: SimpleNamespace(
            password_breach_check=True,
            breach_check_api_url="https://range.example/range/",
            breach_check_timeout_seconds=1.0,
        ),
    )


def _client(respond: httpx.MockTransport) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=respond)


@pytest.mark.asyncio
async def test_only_the_hash_prefix_leaves_the_installation() -> None:
    requested: list[httpx.Request] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requested.append(request)
        return httpx.Response(200, text="0000000000000000000000000000000000A:3\n")

    async with _client(httpx.MockTransport(respond)) as client:
        status = await breached_passwords.breach_status(PASSWORD, client=client)

    assert status == "not_found"
    (request,) = requested
    assert request.url.path == f"/range/{SHA1[:5]}"
    assert request.headers["Add-Padding"] == "true"
    assert PASSWORD not in str(request.url)
    assert SHA1[5:] not in str(request.url)


@pytest.mark.asyncio
async def test_a_breached_password_is_refused() -> None:
    body = f"{SHA1[5:]}:42\r\nABCDEF0123456789ABCDEF0123456789ABC:1"
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=body))

    async with _client(transport) as client:
        with pytest.raises(ElanoraError) as refused:
            await breached_passwords.refuse_breached_password(PASSWORD, client=client)

    assert refused.value.code == ErrorCode.PASSWORD_BREACHED


@pytest.mark.asyncio
async def test_padding_entries_are_not_breaches() -> None:
    transport = httpx.MockTransport(lambda _: httpx.Response(200, text=f"{SHA1[5:]}:0"))
    async with _client(transport) as client:
        assert (
            await breached_passwords.breach_status(PASSWORD, client=client)
            == "not_found"
        )


@pytest.mark.asyncio
async def test_an_unreachable_service_does_not_block_the_researcher() -> None:
    def fail(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    async with _client(httpx.MockTransport(fail)) as client:
        assert (
            await breached_passwords.breach_status(PASSWORD, client=client)
            == "unavailable"
        )
        await breached_passwords.refuse_breached_password(PASSWORD, client=client)


@pytest.mark.asyncio
async def test_the_check_can_be_turned_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        breached_passwords,
        "get_settings",
        lambda: SimpleNamespace(password_breach_check=False),
    )

    def never(request: httpx.Request) -> httpx.Response:
        raise AssertionError("the breach service must not be called")

    async with _client(httpx.MockTransport(never)) as client:
        await breached_passwords.refuse_breached_password(PASSWORD, client=client)
