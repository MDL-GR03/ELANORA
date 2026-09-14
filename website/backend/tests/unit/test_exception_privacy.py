"""Tests for safe, stable HTTP exception responses and diagnostics."""

import ast
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

import app.api.v1.review as review_api
import app.core.exception_handler as exception_handler_module
import app.middleware.csrf as csrf_module
from app.api.v1.protocol import _domain_http_error
from app.core.exception_handler import (
    add_general_exception_handler,
    validation_exception_handler,
)
from app.middleware.csrf import CSRFMiddleware
from app.schema.review import ReviewCaseCreate

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


@pytest.mark.asyncio
async def test_review_domain_failure_does_not_publish_exception_text(
    monkeypatch,
) -> None:
    async def fail(*_args, **_kwargs):
        raise ValueError(SENSITIVE_VALUE)

    monkeypatch.setattr(review_api, "create_case", fail)
    access = SimpleNamespace(
        project=SimpleNamespace(project_id=7),
        user=SimpleNamespace(user_id=11),
    )

    with pytest.raises(HTTPException) as raised:
        await review_api.post_review_case(
            7,
            ReviewCaseCreate(upload_id=1, title="Review"),
            Mock(),
            access,
        )

    assert raised.value.status_code == 422
    assert raised.value.detail == review_api.INVALID_REVIEW_OPERATION
    assert SENSITIVE_VALUE not in str(raised.value.detail)


def test_protocol_domain_failure_does_not_publish_exception_text() -> None:
    public_error = _domain_http_error(RuntimeError(SENSITIVE_VALUE))

    assert public_error.status_code == 409
    assert public_error.detail == "Protocol state conflict"
    assert SENSITIVE_VALUE not in str(public_error.detail)


def test_api_boundary_never_serializes_caught_exception_text() -> None:
    source_root = Path(__file__).parents[2] / "app"
    violations: list[str] = []
    caught_names = {"e", "err", "error", "exc", "exception"}

    for directory in (source_root / "api", source_root / "dependency"):
        for source_path in directory.rglob("*.py"):
            tree = ast.parse(source_path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                if not isinstance(node.func, ast.Name) or node.func.id != "str":
                    continue
                if not node.args or not isinstance(node.args[0], ast.Name):
                    continue
                if node.args[0].id in caught_names:
                    violations.append(
                        f"{source_path.relative_to(source_root)}:{node.lineno}"
                    )

    assert violations == []
