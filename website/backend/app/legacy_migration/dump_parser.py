"""Small, strict reader for values in the pinned legacy MySQL dump.

This is intentionally not a general SQL parser. It only reads INSERT rows from
the reviewed dump and never executes MySQL text against PostgreSQL.
"""

import hashlib
import re
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

EXPECTED_DUMP_SHA256 = (
    "2b0153b23d047a76e3b71ff5adba90d9f817a3c18049c6763a30f2b47db68582"
)
_CREATE_TABLE = re.compile(r"^CREATE TABLE `(?P<table>[^`]+)` \($")
_COLUMN = re.compile(r"^  `(?P<column>[^`]+)` ")
_INSERT = re.compile(r"^INSERT INTO `(?P<table>[^`]+)` VALUES (?P<values>.*);$")

type SqlScalar = str | int | Decimal | None


@dataclass(frozen=True, slots=True)
class LegacyTable:
    """Column names and decoded rows for one source table."""

    columns: tuple[str, ...]
    rows: tuple[dict[str, SqlScalar], ...]


class LegacyDumpError(ValueError):
    """Raised when the legacy dump is unexpected or cannot be decoded safely."""


def verify_dump(path: Path) -> None:
    """Refuse an unknown dump so positional INSERT mappings cannot silently drift."""
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != EXPECTED_DUMP_SHA256:
        raise LegacyDumpError(
            "legacy dump checksum differs from the reviewed source: "
            f"expected {EXPECTED_DUMP_SHA256}, got {digest}"
        )


def read_tables(path: Path, selected: Sequence[str]) -> dict[str, LegacyTable]:
    """Read selected tables without loading unrelated or derived rows into memory."""
    wanted = set(selected)
    columns: dict[str, tuple[str, ...]] = {}
    rows: dict[str, list[dict[str, SqlScalar]]] = {name: [] for name in wanted}
    current_table: str | None = None
    current_columns: list[str] = []

    with path.open(encoding="utf-8") as stream:
        for raw_line in stream:
            line = raw_line.rstrip("\n")
            create_match = _CREATE_TABLE.match(line)
            if create_match:
                current_table = create_match.group("table")
                current_columns = []
                continue
            if current_table is not None:
                column_match = _COLUMN.match(line)
                if column_match:
                    current_columns.append(column_match.group("column"))
                    continue
                if line.startswith(") ENGINE="):
                    if current_table in wanted:
                        columns[current_table] = tuple(current_columns)
                    current_table = None
                    current_columns = []
                    continue

            insert_match = _INSERT.match(line)
            if not insert_match or insert_match.group("table") not in wanted:
                continue
            table_name = insert_match.group("table")
            table_columns = columns.get(table_name)
            if table_columns is None:
                raise LegacyDumpError(f"INSERT appeared before schema for {table_name}")
            for values in _parse_tuples(insert_match.group("values")):
                if len(values) != len(table_columns):
                    raise LegacyDumpError(
                        f"{table_name} row has {len(values)} values for "
                        f"{len(table_columns)} columns"
                    )
                rows[table_name].append(dict(zip(table_columns, values, strict=True)))

    missing = wanted.difference(columns)
    if missing:
        raise LegacyDumpError(f"tables absent from legacy dump: {sorted(missing)}")
    return {
        name: LegacyTable(columns=columns[name], rows=tuple(rows[name]))
        for name in selected
    }


def _parse_tuples(text: str) -> Iterator[tuple[SqlScalar, ...]]:
    position = 0
    while position < len(text):
        if text[position] != "(":
            raise LegacyDumpError(f"expected '(' at character {position}")
        position += 1
        values: list[SqlScalar] = []
        while True:
            value, position = _parse_value(text, position)
            values.append(value)
            if position >= len(text):
                raise LegacyDumpError("unterminated INSERT tuple")
            delimiter = text[position]
            position += 1
            if delimiter == ")":
                break
            if delimiter != ",":
                raise LegacyDumpError(f"unexpected delimiter {delimiter!r}")
        yield tuple(values)
        if position == len(text):
            return
        if text[position] != ",":
            raise LegacyDumpError(f"expected tuple separator at character {position}")
        position += 1


def _parse_value(text: str, position: int) -> tuple[SqlScalar, int]:
    if position >= len(text):
        raise LegacyDumpError("missing value")
    if text[position] == "'":
        return _parse_string(text, position + 1)

    end = position
    while end < len(text) and text[end] not in ",)":
        end += 1
    literal = text[position:end]
    if literal == "NULL":
        return None, end
    try:
        return (Decimal(literal) if "." in literal else int(literal)), end
    except ValueError as error:
        raise LegacyDumpError(f"unsupported unquoted value {literal!r}") from error


def _parse_string(text: str, position: int) -> tuple[str, int]:
    output: list[str] = []
    escapes = {
        "0": "\0",
        "b": "\b",
        "n": "\n",
        "r": "\r",
        "t": "\t",
        "Z": "\x1a",
        "'": "'",
        '"': '"',
        "\\": "\\",
    }
    while position < len(text):
        character = text[position]
        position += 1
        if character == "'":
            return "".join(output), position
        if character == "\\":
            if position >= len(text):
                raise LegacyDumpError("unterminated string escape")
            escaped = text[position]
            position += 1
            output.append(escapes.get(escaped, escaped))
        else:
            output.append(character)
    raise LegacyDumpError("unterminated string value")
