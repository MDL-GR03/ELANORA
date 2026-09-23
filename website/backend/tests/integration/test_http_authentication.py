"""Signing in, cookies, CSRF, refresh and sign-out through the real application."""

from http.cookies import SimpleCookie

import pytest
from conftest import ACCOUNT_PASSWORD, InstitutionAccounts
from httpx import AsyncClient, Response

LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/user/me"


def _set_cookies(response: Response) -> dict[str, SimpleCookie]:
    cookies = {}
    for header in response.headers.get_list("set-cookie"):
        parsed = SimpleCookie()
        parsed.load(header)
        for name in parsed:
            cookies[name] = parsed
    return cookies


def _replay(client: AsyncClient, **cookies: str) -> None:
    """Replace the browser's cookies with copies an attacker kept."""
    client.cookies.clear()
    for name, value in cookies.items():
        path = "/api/v1/auth" if name == "elanora_refresh" else "/"
        client.cookies.set(name, value, domain="localhost.local", path=path)


async def _sign_in(client: AsyncClient, login: str) -> str:
    response = await client.post(
        LOGIN, json={"login": login, "password": ACCOUNT_PASSWORD}
    )
    assert response.status_code == 200, response.text
    return response.json()["csrf_token"]


@pytest.mark.asyncio
async def test_signing_in_sets_protected_session_cookies(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    response = await api_client.post(
        LOGIN,
        json={
            "login": institution_accounts.researcher_login,
            "password": ACCOUNT_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    cookies = _set_cookies(response)
    session = cookies["elanora_session"]["elanora_session"]
    refresh = cookies["elanora_refresh"]["elanora_refresh"]
    csrf = cookies["elanora_csrf"]["elanora_csrf"]
    assert session["httponly"] and refresh["httponly"]
    assert not csrf["httponly"], "the frontend must read the CSRF token"
    # Sign-out has to receive this cookie to revoke the session.
    assert LOGOUT.startswith(refresh["path"]) and REFRESH.startswith(refresh["path"])
    assert {session["samesite"], refresh["samesite"], csrf["samesite"]} == {"lax"}
    assert response.json()["csrf_token"] == csrf.value
    me = await api_client.get(ME)
    assert me.status_code == 200
    assert me.json()["username"] == institution_accounts.researcher_login


@pytest.mark.asyncio
async def test_a_wrong_password_and_an_unknown_account_look_the_same(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    wrong = await api_client.post(
        LOGIN,
        json={"login": institution_accounts.researcher_login, "password": "nope"},
    )
    unknown = await api_client.post(
        LOGIN, json={"login": "nobody-here", "password": "nope"}
    )

    assert wrong.status_code == unknown.status_code == 400
    wrong_data = wrong.json()
    unknown_data = unknown.json()
    wrong_data.pop("correlation_id")
    unknown_data.pop("correlation_id")
    assert wrong_data == unknown_data
    assert "set-cookie" not in wrong.headers
    assert (await api_client.get(ME)).status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize("header", [None, "forged-token"])
async def test_state_changes_need_the_matching_csrf_header(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    header: str | None,
) -> None:
    await _sign_in(api_client, institution_accounts.researcher_login)

    response = await api_client.post(
        LOGOUT, headers={} if header is None else {"X-CSRF-Token": header}
    )

    assert response.status_code == 403
    assert (await api_client.get(ME)).status_code == 200


@pytest.mark.asyncio
async def test_refreshing_rotates_the_refresh_token(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    csrf = await _sign_in(api_client, institution_accounts.researcher_login)
    stolen = api_client.cookies.get("elanora_refresh")

    refreshed = await api_client.post(REFRESH, headers={"X-CSRF-Token": csrf})
    assert refreshed.status_code == 200
    assert api_client.cookies.get("elanora_refresh") != stolen

    _replay(api_client, elanora_refresh=stolen, elanora_csrf=csrf)
    replayed = await api_client.post(REFRESH, headers={"X-CSRF-Token": csrf})
    assert replayed.status_code == 401


@pytest.mark.asyncio
async def test_signing_out_revokes_the_refresh_session(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    """A copied refresh cookie must stop working once its owner signs out."""
    csrf = await _sign_in(api_client, institution_accounts.researcher_login)
    copied = api_client.cookies.get("elanora_refresh")

    signed_out = await api_client.post(LOGOUT, headers={"X-CSRF-Token": csrf})
    assert signed_out.status_code == 200
    cleared = signed_out.headers.get_list("set-cookie")
    assert any(
        "elanora_refresh=" in header and "Path=/api/v1/auth/refresh" in header
        for header in cleared
    ), "cookies issued under the old path must be cleared too"
    assert (await api_client.get(ME)).status_code == 401

    _replay(api_client, elanora_refresh=copied, elanora_csrf=csrf)
    replayed = await api_client.post(REFRESH, headers={"X-CSRF-Token": csrf})
    assert replayed.status_code == 401
