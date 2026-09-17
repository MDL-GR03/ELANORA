"""Controlled MySQL-dump to PostgreSQL migration for the legacy ELANORA data."""

import shutil
import subprocess
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import sqlalchemy as sa
from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

import app.model  # noqa: F401 - registers every mapped table
from app.db.database import Base
from app.legacy_migration.dump_parser import SqlScalar, read_tables
from app.model.annotation import Annotation
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.instance import Instance
from app.model.project import Project
from app.model.tier import Tier
from app.model.user import User
from app.service.elan import ElanService
from app.storage.paths import safe_project_path

COPIED_TABLES = (
    "INSTANCE",
    "COUNTRY",
    "CITY",
    "ADDRESS",
    "USER",
    "PROJECT",
    "FILE_TYPE",
    "ACCEPTED_VALUE",
    "ANNOTATION_STANDARD",
    "COMPONENT_TEMPLATE",
    "COMPONENT_ACCEPTED_VALUE",
    "PROJECT_ANNOT_STANDARD",
    "PROJECT_FILE_TYPE",
    "PROJECT_LOCATION_FILE_TYPE",
    "PROJECT_NAMING_STANDARD",
    "STANDARD_COMPONENT",
    "EFFECTIVE_NAMING_STANDARD",
    "TIER_SECTION",
    "USER_TO_PROJECT",
)


@dataclass(frozen=True, slots=True)
class MigrationReport:
    """Reconciled source and target counts from a completed migration."""

    copied_rows: dict[str, int]
    source_eaf_files: int
    imported_eaf_files: int
    imported_revisions: int
    imported_tiers: int
    imported_annotations: int


async def migrate_legacy_database(
    db: AsyncSession,
    *,
    dump_path: Path,
    source_files: Path,
    projects_root: Path,
) -> MigrationReport:
    """Import an empty target using relational metadata plus validated EAF sources."""
    source = read_tables(dump_path, (*COPIED_TABLES, "ELAN_FILE"))
    await _require_empty_target(db)

    instance_rows = source["INSTANCE"].rows
    if len(instance_rows) != 1:
        raise ValueError("legacy import requires exactly one institutional instance")
    instance_id = int(_required(instance_rows[0], "instance_id"))

    copied_rows: dict[str, int] = {}
    for table_name in COPIED_TABLES:
        records = [
            _transform_row(
                table_name,
                row,
                instance_id=instance_id,
                projects_root=projects_root,
            )
            for row in source[table_name].rows
        ]
        if records:
            table = Base.metadata.tables[table_name]
            converted = [_coerce_row(table, record) for record in records]
            await db.execute(insert(table), converted)
        copied_rows[table_name] = len(records)

    await _reset_sequences(db, COPIED_TABLES)
    await db.commit()

    eaf_rows = source["ELAN_FILE"].rows
    await _install_and_ingest_eaf_sources(
        db,
        eaf_rows=eaf_rows,
        source_files=source_files,
        projects_root=projects_root,
    )

    imported_eaf_files = await db.scalar(select(func.count()).select_from(ElanFile))
    imported_revisions = await db.scalar(select(func.count()).select_from(EafRevision))
    imported_tiers = await db.scalar(select(func.count()).select_from(Tier))
    imported_annotations = await db.scalar(select(func.count()).select_from(Annotation))
    if imported_eaf_files != len(eaf_rows) or imported_revisions != len(eaf_rows):
        raise RuntimeError(
            "EAF reconciliation failed: "
            f"source={len(eaf_rows)}, files={imported_eaf_files}, "
            f"revisions={imported_revisions}"
        )

    return MigrationReport(
        copied_rows=copied_rows,
        source_eaf_files=len(eaf_rows),
        imported_eaf_files=imported_eaf_files or 0,
        imported_revisions=imported_revisions or 0,
        imported_tiers=imported_tiers or 0,
        imported_annotations=imported_annotations or 0,
    )


async def _require_empty_target(db: AsyncSession) -> None:
    instances = await db.scalar(select(func.count()).select_from(Instance))
    users = await db.scalar(select(func.count()).select_from(User))
    projects = await db.scalar(select(func.count()).select_from(Project))
    if instances or users or projects:
        raise RuntimeError(
            "legacy migration refused: target must be a freshly migrated, empty database"
        )


def _transform_row(
    table_name: str,
    row: dict[str, SqlScalar],
    *,
    instance_id: int,
    projects_root: Path,
) -> dict[str, SqlScalar]:
    transformed = dict(row)
    if table_name == "USER":
        transformed["instance_id"] = instance_id
    elif table_name == "PROJECT":
        project_name = str(_required(row, "project_name"))
        transformed["description"] = row.get("description") or ""
        transformed["project_path"] = str(
            safe_project_path(projects_root, project_name)
        )
        transformed["deleted_at"] = None
    return transformed


def _coerce_row(table: sa.Table, row: dict[str, SqlScalar]) -> dict[str, Any]:
    converted: dict[str, Any] = {}
    for column in table.columns:
        if column.name not in row:
            continue
        value: Any = row[column.name]
        if value is None:
            converted[column.name] = None
        elif isinstance(column.type, sa.Boolean):
            converted[column.name] = bool(value)
        elif isinstance(column.type, sa.DateTime) and isinstance(value, str):
            converted[column.name] = datetime.fromisoformat(value)
        elif isinstance(column.type, sa.Integer) and isinstance(value, Decimal):
            converted[column.name] = int(value)
        else:
            converted[column.name] = value
    return converted


async def _reset_sequences(db: AsyncSession, table_names: tuple[str, ...]) -> None:
    for table_name in table_names:
        table = Base.metadata.tables[table_name]
        for column in table.primary_key.columns:
            if table._autoincrement_column is not column:
                continue
            quoted_table = f'"{table_name}"'
            sequence_name = await db.scalar(
                select(func.pg_get_serial_sequence(quoted_table, column.name))
            )
            if sequence_name is None:
                continue
            maximum = await db.scalar(select(func.max(column)))
            await db.execute(
                select(func.setval(sequence_name, maximum or 1, maximum is not None))
            )


async def _install_and_ingest_eaf_sources(
    db: AsyncSession,
    *,
    eaf_rows: tuple[dict[str, SqlScalar], ...],
    source_files: Path,
    projects_root: Path,
) -> None:
    projects = {
        project.project_id: project
        for project in (await db.scalars(select(Project))).all()
    }
    users = list((await db.scalars(select(User).order_by(User.user_id))).all())
    instance = await db.scalar(select(Instance))
    if not users:
        raise RuntimeError("legacy migration has no user to own imported files")
    if instance is None:
        raise RuntimeError("legacy migration has no institutional instance")
    importer_id = users[0].user_id

    expected_by_project: dict[int, int] = {}
    for row in eaf_rows:
        project_id = int(_required(row, "project_id"))
        expected_by_project[project_id] = expected_by_project.get(project_id, 0) + 1

    service = ElanService(db)
    for project_id, expected_count in expected_by_project.items():
        project = projects.get(project_id)
        if project is None:
            raise RuntimeError(f"legacy EAF references missing project {project_id}")
        source_directory = _match_project_directory(source_files, project.project_name)
        eaf_paths = sorted(source_directory.glob("*.eaf"))
        if len(eaf_paths) != expected_count:
            raise RuntimeError(
                f"project {project.project_name!r} has {len(eaf_paths)} source EAFs; "
                f"legacy database expects {expected_count}"
            )

        project_path = safe_project_path(projects_root, project.project_name)
        if project_path.exists():
            raise RuntimeError(
                f"target project directory already exists: {project_path}"
            )
        elan_directory = project_path / "elan_files"
        elan_directory.mkdir(parents=True)
        for source_path in eaf_paths:
            shutil.copy2(source_path, elan_directory / source_path.name)

        _initialize_repository(project_path, instance.instance_name)
        for target_path in sorted(elan_directory.glob("*.eaf")):
            result = await service.process_single_file(
                str(target_path), importer_id, project.project_name
            )
            if result.status != "processed":
                raise RuntimeError(f"failed to import {target_path.name}: {result}")


def _match_project_directory(source_root: Path, project_name: str) -> Path:
    expected = _fold_name(project_name)
    matches = [
        child
        for child in source_root.iterdir()
        if child.is_dir() and _fold_name(child.name) == expected
    ]
    if len(matches) != 1:
        raise RuntimeError(
            f"expected one source directory for project {project_name!r}, found {matches}"
        )
    return matches[0]


def _fold_name(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.casefold())
    return "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )


def _initialize_repository(project_path: Path, instance_name: str) -> None:
    (project_path / ".gitignore").write_text(
        "*\n!*.md\n!.gitignore\n!elan_files/\n!elan_files/*.eaf\n",
        encoding="utf-8",
    )
    (project_path / "README.md").write_text(
        f"# {project_path.name}\n\nMigrated ELANORA research project.\n",
        encoding="utf-8",
    )
    commands = (
        ("init", "--initial-branch=main"),
        ("config", "user.name", instance_name),
        ("config", "user.email", "migration@elanora.local"),
        ("add", "."),
        ("commit", "-m", "Import legacy ELANORA project"),
    )
    for arguments in commands:
        subprocess.run(
            ["git", *arguments],
            cwd=project_path,
            check=True,
            capture_output=True,
            text=True,
        )


def _required(row: dict[str, SqlScalar], key: str) -> str | int | Decimal:
    value = row.get(key)
    if value is None:
        raise ValueError(f"legacy row is missing required value {key}")
    return value
