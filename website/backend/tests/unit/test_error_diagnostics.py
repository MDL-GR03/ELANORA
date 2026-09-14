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


def test_invitation_logs_exclude_personal_data_and_tracebacks() -> None:
    source_root = Path(__file__).parents[2] / "app"
    source_path = source_root / "service/invitation.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    forbidden_extra_keys = {
        "admin_user_id",
        "email",
        "error",
        "invitation_code",
        "invitation_id",
        "new_member_name",
        "notification_id",
        "project_id",
        "receiver_email",
        "sender_id",
        "user_id",
    }
    violations: list[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        if not isinstance(node.func.value, ast.Name) or node.func.value.id != "logger":
            continue
        for keyword in node.keywords:
            if keyword.arg == "exc_info":
                violations.append(f"traceback:{node.lineno}")
            if keyword.arg != "extra" or not isinstance(keyword.value, ast.Dict):
                continue
            for key in keyword.value.keys:
                if isinstance(key, ast.Constant) and key.value in forbidden_extra_keys:
                    violations.append(f"{key.value}:{node.lineno}")

    assert violations == []
