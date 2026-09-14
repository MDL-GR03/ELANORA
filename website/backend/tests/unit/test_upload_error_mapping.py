"""The upload endpoint must report a bad filename as itself, not as a 400.

FilenameNotCompliantError subclasses ValueError, which the same handler maps to
a generic "Invalid project operation". If the specific handler is ever reordered
below that one, researchers stop being told which file to rename, so the order
is asserted here rather than left to review.
"""

import ast
import inspect
from pathlib import Path

import app.api.v1.git as git_api
from app.service.upload_naming_compliance import FilenameNotCompliantError

API_SOURCE = Path(inspect.getfile(git_api))


def _upload_handler() -> ast.AsyncFunctionDef:
    tree = ast.parse(API_SOURCE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and any(
            isinstance(handler.type, ast.Name)
            and handler.type.id == "FilenameNotCompliantError"
            for stmt in ast.walk(node)
            if isinstance(stmt, ast.Try)
            for handler in stmt.handlers
        ):
            return node
    raise AssertionError("No upload handler catches FilenameNotCompliantError")


def _handled_names(node: ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    for stmt in ast.walk(node):
        if not isinstance(stmt, ast.Try):
            continue
        for handler in stmt.handlers:
            if isinstance(handler.type, ast.Name):
                names.append(handler.type.id)
            elif isinstance(handler.type, ast.Tuple):
                names.extend(
                    element.id
                    for element in handler.type.elts
                    if isinstance(element, ast.Name)
                )
    return names


def test_the_specific_filename_error_is_caught_before_value_error() -> None:
    names = _handled_names(_upload_handler())

    assert "FilenameNotCompliantError" in names
    assert "ValueError" in names
    assert names.index("FilenameNotCompliantError") < names.index("ValueError")


def test_the_error_still_subclasses_value_error() -> None:
    """If this stops being true the ordering above stops mattering."""
    assert issubclass(FilenameNotCompliantError, ValueError)


def test_the_reported_detail_identifies_the_file_without_leaking_internals() -> None:
    error = FilenameNotCompliantError("session 12.eaf", pattern="{subject}-{session}")

    assert error.filename == "session 12.eaf"
    assert error.pattern == "{subject}-{session}"
    assert "does not comply" in str(error)
