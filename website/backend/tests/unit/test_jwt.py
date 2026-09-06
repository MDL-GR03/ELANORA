from datetime import timedelta

import pytest
from fastapi import HTTPException

import app.core.jwt as jwt_service
from app.schema.common.token import TokenData

TEST_SECRET = "unit-test-secret-with-at-least-32-characters"  # noqa: S105


@pytest.fixture(autouse=True)
def configured_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(jwt_service, "JWT_SECRET_KEY", TEST_SECRET)


def test_access_token_round_trip() -> None:
    token = jwt_service.create_access_token(TokenData(sub="42"))

    assert jwt_service.verify_token(token) == TokenData(sub="42")


def test_refresh_token_cannot_be_used_as_access_token() -> None:
    token = jwt_service.create_refresh_token(TokenData(sub="42"))

    with pytest.raises(HTTPException) as error:
        jwt_service.verify_token(token)

    assert error.value.status_code == 401


def test_expired_or_tampered_token_is_rejected() -> None:
    expired = jwt_service.create_access_token(
        TokenData(sub="42"), expires_delta=timedelta(seconds=-30)
    )
    valid = jwt_service.create_access_token(TokenData(sub="42"))
    header, payload, signature = valid.split(".")
    replacement = "A" if signature[0] != "A" else "B"
    tampered = f"{header}.{payload}.{replacement}{signature[1:]}"

    for token in (expired, tampered):
        with pytest.raises(HTTPException) as error:
            jwt_service.verify_token(token)
        assert error.value.status_code == 401
