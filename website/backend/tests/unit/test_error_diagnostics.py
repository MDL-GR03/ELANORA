"""Regression tests for diagnostics stored or emitted outside a request."""

import ast
from pathlib import Path

from app.core.error_diagnostics import safe_exception_type, safe_failure_summary

SENSITIVE_VALUE = "/srv/private/project?token=do-not-store"


def test_safe_failure_summary_excludes_exception_message() -> None:
    summary = safe_failure_summary(
        RuntimeError(SENSITIVE_VALUE), operation="Project synchronization failed"
    )

    assert summary == "Project synchronization failed; error_type=RuntimeError"
    assert SENSITIVE_VALUE not in summary


def test_safe_exception_type_rejects_unbounded_dynamic_class_names() -> None:
    unsafe_type = type("X" * 100, (Exception,), {})

    assert safe_exception_type(unsafe_type(SENSITIVE_VALUE)) == "Exception"


def test_durable_workflow_failures_never_copy_caught_exception_text() -> None:
    source_root = Path(__file__).parents[2] / "app"
    service_files = (
        "service/contribution_change_set.py",
        "service/elan.py",
        "service/git.py",
        "service/git_operations.py",
        "service/outbox.py",
        "service/project_integrity.py",
        "service/project_sync.py",
    )
    caught_names = {"e", "err", "error", "exc", "exception"}
    violations: list[str] = []

    for relative_path in service_files:
        source_path = source_root / relative_path
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Name) or node.func.id != "str":
                continue
            if not node.args or not isinstance(node.args[0], ast.Name):
                continue
            if node.args[0].id in caught_names:
                violations.append(f"{relative_path}:{node.lineno}")

    assert violations == []
