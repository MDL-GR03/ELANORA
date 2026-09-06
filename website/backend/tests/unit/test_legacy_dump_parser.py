from pathlib import Path

import pytest

from app.legacy_migration.dump_parser import LegacyDumpError, read_tables


def test_read_tables_decodes_mysql_literals(tmp_path: Path) -> None:
    dump = tmp_path / "legacy.sql"
    dump.write_text(
        "CREATE TABLE `EXAMPLE` (\n"
        "  `id` int NOT NULL,\n"
        "  `label` varchar(100) DEFAULT NULL\n"
        ") ENGINE=InnoDB;\n"
        "INSERT INTO `EXAMPLE` VALUES "
        "(1,'researcher\\'s file'),(2,'C:\\\\corpus\\\\sample'),(3,NULL);\n",
        encoding="utf-8",
    )

    table = read_tables(dump, ["EXAMPLE"])["EXAMPLE"]

    assert table.columns == ("id", "label")
    assert table.rows == (
        {"id": 1, "label": "researcher's file"},
        {"id": 2, "label": "C:\\corpus\\sample"},
        {"id": 3, "label": None},
    )


def test_read_tables_rejects_positional_schema_mismatch(tmp_path: Path) -> None:
    dump = tmp_path / "legacy.sql"
    dump.write_text(
        "CREATE TABLE `EXAMPLE` (\n"
        "  `id` int NOT NULL\n"
        ") ENGINE=InnoDB;\n"
        "INSERT INTO `EXAMPLE` VALUES (1,'unexpected');\n",
        encoding="utf-8",
    )

    with pytest.raises(LegacyDumpError, match="2 values for 1 columns"):
        read_tables(dump, ["EXAMPLE"])
