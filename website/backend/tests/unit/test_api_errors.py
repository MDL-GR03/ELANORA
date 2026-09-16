"""Every refusal the API returns is identified by a code the interface translates."""

import ast
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.errors import ERRORS, ElanoraError, ErrorCode, elanora_error_handler

APP_ROOT = Path(__file__).parents[2] / "app"


def test_every_code_has_a_status_and_message() -> None:
    assert set(ERRORS) == set(ErrorCode)
    for code, definition in ERRORS.items():
        assert 400 <= definition.status < 600, code
        assert definition.message, code


def test_a_refusal_reaches_the_client_with_its_code_and_parameters() -> None:
    app = FastAPI()
    app.add_exception_handler(ElanoraError, elanora_error_handler)

    @app.get("/busy")
    async def busy() -> None:
        raise ElanoraError(ErrorCode.UPLOAD_FILE_TOO_LARGE, max_mb=50)

    response = TestClient(app).get("/busy")

    assert response.status_code == 400
    assert response.json() == {
        "detail": "File too large. Maximum size is 50 MB per file",
        "code": "upload_file_too_large",
        "params": {"max_mb": 50},
    }


def test_a_message_with_a_missing_parameter_still_renders() -> None:
    assert ElanoraError(ErrorCode.UPLOAD_EAF_INVALID).message.startswith(
        "Invalid ELAN file"
    )


@pytest.mark.parametrize("path", sorted(APP_ROOT.rglob("*.py")), ids=str)
def test_the_application_raises_no_untranslatable_http_errors(path: Path) -> None:
    """A bare HTTPException would reach researchers as untranslated English."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    raised = [
        node.lineno
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and getattr(node.func, "id", getattr(node.func, "attr", None))
        == "HTTPException"
    ]
    assert raised == [], f"{path.relative_to(APP_ROOT)} raises HTTPException"
