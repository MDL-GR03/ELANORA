"""Every instant ELANORA records or reports is an explicit UTC time.

Naive times meant different things depending on where they were written:
PostgreSQL's clock, or the server process's local clock. Stored in a
timezone-aware column they were read as UTC, and serialized without an offset
browsers read them as the viewer's local time.
"""

import ast
from pathlib import Path

from sqlalchemy import DateTime

import app.model  # noqa: F401 - registers every table
from app.db.database import Base

APP_ROOT = Path(__file__).parents[2] / "app"


def _call_name(node: ast.Call) -> str:
    parts = []
    target = node.func
    while isinstance(target, ast.Attribute):
        parts.append(target.attr)
        target = target.value
    if isinstance(target, ast.Name):
        parts.append(target.id)
    return ".".join(reversed(parts))


def _reads_naive_clock(node: ast.Call) -> bool:
    name = _call_name(node)
    zoned = any(keyword.arg == "tz" for keyword in node.keywords)
    if name.endswith(("datetime.now", "datetime.today")):
        return not (node.args or zoned)
    if name.endswith("datetime.fromtimestamp"):
        return not (len(node.args) > 1 or zoned)
    return name.endswith(
        ("datetime.utcnow", "func.current_timestamp", "func.localtimestamp")
    )


def _naive_clock_calls(source: str) -> list[tuple[int, str]]:
    return [
        (node.lineno, _call_name(node))
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Call) and _reads_naive_clock(node)
    ]


def test_every_timestamp_column_stores_a_time_zone() -> None:
    naive = sorted(
        f"{table.name}.{column.name}"
        for table in Base.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, DateTime) and not column.type.timezone
    )

    assert naive == []


def test_application_code_never_reads_a_naive_clock() -> None:
    offenders = [
        f"{path.relative_to(APP_ROOT.parent)}:{line} {name}"
        for path in sorted(APP_ROOT.rglob("*.py"))
        for line, name in _naive_clock_calls(path.read_text(encoding="utf-8"))
    ]

    assert offenders == []


def test_the_guardrail_recognises_each_naive_form() -> None:
    source = """
from datetime import UTC, datetime
import datetime as dt
datetime.now()
dt.datetime.now()
datetime.utcnow()
datetime.fromtimestamp(1)
func.current_timestamp()
datetime.now(UTC)
datetime.now(tz=UTC)
datetime.fromtimestamp(1, UTC)
"""

    assert [line for line, _ in _naive_clock_calls(source)] == [4, 5, 6, 7, 8]
