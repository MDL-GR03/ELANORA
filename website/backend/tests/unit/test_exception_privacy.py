"""Tests for safe, stable HTTP exception responses and diagnostics."""

import json
from unittest.mock import Mock

import pytest
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

import app.core.exception_handler as exception_handler_module
import app.middleware.csrf as csrf_module
from app.core.exception_handler import (
    add_general_exception_handler,
    validation_exception_handler,
)
from app.middleware.csrf import CSRFMiddleware

SENSITIVE_VALUE = "participant-secret@example.org?token=do-not-log"


def _request() -> Request:
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/private",
            "query_string": f"email={SENSITIVE_VALUE}".encode(),
            "headers": [(b"user-agent", SENSITIVE_VALUE.encode())],
            "client": (SENSITIVE_VALUE, 1234),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )
    request.state.correlation_id = "safe-correlation-id"
    return request


def _calls(logger: Mock) -> str:
    return repr(logger.method_calls)


@pytest.mark.asyncio
async def test_validation_handler_does_not_echo_input_or_request_secrets(
    monkeypatch,
) -> None:
    logger = Mock()
    monkeypatch.setattr(
        exception_handler_module, "get_exception_logger", lambda _name: logger
    )
    exc = RequestValidationError(
        [
            {
                "type": "string_too_short",
                "loc": ("body", "summary"),
                "msg": "String should have at least 3 characters",
                "input": SENSITIVE_VALUE,
                "ctx": {"submitted": SENSITIVE_VALUE},
            }
        ]
    )

    response = await validation_exception_handler(_request(), exc)
    payload = json.loads(response.body)

    assert response.status_code == 400
    assert payload["detail"] == [
        {
            "type": "string_too_short",
            "loc": ["body", "summary"],
            "msg": "Invalid request value.",
        }
    ]
    assert SENSITIVE_VALUE not in response.body.decode()
    assert SENSITIVE_VALUE not in _calls(logger)


@pytest.mark.asyncio
async def test_unexpected_exception_handler_hides_message_and_request_secrets(
    monkeypatch,
) -> None:
    logger = Mock()
    monkeypatch.setattr(
        exception_handler_module, "get_exception_logger", lambda _name: logger
    )
    handler = add_general_exception_handler()

    response = await handler(_request(), RuntimeError(SENSITIVE_VALUE))

    assert response.status_code == 500
    assert SENSITIVE_VALUE not in response.body.decode()
    assert SENSITIVE_VALUE not in _calls(logger)
    assert "RuntimeError" in _calls(logger)


@pytest.mark.asyncio
async def test_csrf_failure_log_excludes_client_address(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(csrf_module, "csrf_logger", logger)
    middleware = CSRFMiddleware(lambda _scope, _receive, _send: None)

    response = await middleware.dispatch(_request(), Mock())

    assert response.status_code == 403
    assert SENSITIVE_VALUE not in _calls(logger)
