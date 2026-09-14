from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.api.v1.auth import logout, refresh_tokens
from app.core.config import (
    ACCESS_TOKEN_COOKIE_NAME,
    CSRF_TOKEN_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
)


def _cookie_headers(response: Response) -> str:
    return "\n".join(
        value.decode() for key, value in response.raw_headers if key == b"set-cookie"
    )


@pytest.mark.asyncio
async def test_missing_refresh_token_clears_all_auth_cookies() -> None:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/auth/refresh",
            "query_string": b"",
            "headers": [],
        }
    )
    response = Response()

    with pytest.raises(HTTPException) as caught:
        await refresh_tokens(request, response, AsyncMock(spec=AsyncSession))

    assert caught.value.status_code == 401
    headers = _cookie_headers(response)
    assert ACCESS_TOKEN_COOKIE_NAME in headers
    assert REFRESH_TOKEN_COOKIE_NAME in headers
    assert CSRF_TOKEN_NAME in headers


@pytest.mark.asyncio
async def test_logout_clears_stale_credentials_without_authenticated_user() -> None:
    response = Response()

    result = await logout(response)

    headers = _cookie_headers(response)
    assert "Logged out" in result["message"]
    assert ACCESS_TOKEN_COOKIE_NAME in headers
    assert REFRESH_TOKEN_COOKIE_NAME in headers
    assert CSRF_TOKEN_NAME in headers
    assert response.headers["Cache-Control"] == "no-store"
