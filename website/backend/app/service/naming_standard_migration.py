"""Copy each project's upload naming standard into a protocol draft.

Legacy naming standards are mutable settings, so they cannot show which rules
accepted an earlier revision. This copies the standard that currently governs
a project's uploads into a draft for an administrator to review, publish and
pin. It publishes and pins nothing and leaves the legacy settings untouched, so
every project keeps its present behaviour until someone pins the result.

Running it again creates nothing new for standards already copied.
"""

from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.effective_naming_standard_locations import get_location_id_by_name
from app.crud.effective_naming_standard import get_effective_standards_for_project
from app.crud.project_naming_standard import get_standard_with_components_full
from app.model.audit_event import AuditEvent
from app.model.project import Project
from app.model.protocol import Protocol, ProtocolVersion
from app.schema.protocol import FilenameStandardRule, ProtocolRules
from app.service.protocol_administration import create_protocol, create_protocol_version
from app.service.protocol_errors import ProtocolConflictError
from app.service.protocol_shared import get_pinned_protocol_version
from app.service.upload_naming_compliance import UPLOAD_LOCATION_NAME

PROTOCOL_NAME_SUFFIX = " filename standard"


@dataclass
class NamingStandardCopyReport:
    """What was copied, and why anything with a standard was not."""

    copied: list[dict[str, Any]] = field(default_factory=list)
    skipped: list[dict[str, Any]] = field(default_factory=list)


async def copy_naming_standards_into_protocol_drafts(
    db: AsyncSession, *, dry_run: bool = False
) -> NamingStandardCopyReport:
    """Create a draft per project whose uploads follow a naming standard.

    A project with a pinned protocol gets the next draft of that protocol, its
    rules kept and the filename standard added. Any other project gets a new
    protocol holding only the filename standard. The caller commits; a dry run
    rolls every change back and reports what would happen.
    """
    report = NamingStandardCopyReport()
    location_id = get_location_id_by_name(UPLOAD_LOCATION_NAME)
    if location_id is None:
        return report
    savepoint = await db.begin_nested()
    projects = (await db.scalars(select(Project).order_by(Project.project_id))).all()
    for project in projects:
        await _copy_one(db, project, location_id, report)
    if dry_run:
        await savepoint.rollback()
        for item in report.copied:
            item["protocol_version_id"] = None
    else:
        await savepoint.commit()
    return report


async def _copy_one(
    db: AsyncSession,
    project: Project,
    location_id: int,
    report: NamingStandardCopyReport,
) -> None:
    effective = await get_effective_standards_for_project(
        db, project.project_id, location_id
    )
    if not effective:
        return
    naming_standard_id = effective[0].naming_standard_id
    item: dict[str, Any] = {
        "project_id": project.project_id,
        "project_name": project.project_name,
        "naming_standard_id": naming_standard_id,
    }

    def skip(reason: str) -> None:
        report.skipped.append({**item, "reason": reason})

    full = await get_standard_with_components_full(db, naming_standard_id)
    if full is None:
        skip("standard_not_found")
        return
    try:
        rule = FilenameStandardRule(
            name=full["name"],
            pattern=full["pattern"],
            components=[
                {
                    "name": component["name"],
                    "regex": component["regex"] or "",
                    "accepted_values": component["accepted_values"],
                }
                for component in full["components"]
            ],
        )
    except ValidationError:
        skip("unusable_standard")
        return

    try:
        pinned = await get_pinned_protocol_version(db, project)
    except ProtocolConflictError:
        skip("pinned_protocol_unavailable")
        return

    if pinned is not None:
        pinned_rules = ProtocolRules.model_validate(pinned.rules)
        if pinned_rules.filename_standard is not None:
            skip("protocol_has_filename_standard")
            return
        siblings = (
            await db.scalars(
                select(ProtocolVersion).where(
                    ProtocolVersion.protocol_id == pinned.protocol_id
                )
            )
        ).all()
        if any(_holds(version, rule) for version in siblings):
            skip("already_copied")
            return
        version = await create_protocol_version(
            db,
            project=project,
            protocol_id=pinned.protocol_id,
            rules=pinned_rules.model_copy(update={"filename_standard": rule}),
            actor_user_id=None,
        )
    else:
        name = (project.project_name + PROTOCOL_NAME_SUFFIX)[:150]
        existing = await db.scalar(
            select(Protocol).where(
                Protocol.instance_id == project.instance_id, Protocol.name == name
            )
        )
        if existing is not None:
            versions = (
                await db.scalars(
                    select(ProtocolVersion).where(
                        ProtocolVersion.protocol_id == existing.protocol_id
                    )
                )
            ).all()
            skip(
                "already_copied"
                if any(_holds(version, rule) for version in versions)
                else "protocol_name_taken"
            )
            return
        protocol = await create_protocol(
            db,
            project=project,
            name=name,
            description=(
                f"Copied from the upload naming standard {rule.name!r} for review "
                "before publication."
            ),
            rules=ProtocolRules(filename_standard=rule),
            actor_user_id=None,
        )
        version = protocol.versions[0]

    db.add(
        AuditEvent(
            actor_user_id=None,
            project_id=project.project_id,
            action="protocol.naming_standard.copied",
            resource_type="protocol_version",
            resource_id=str(version.protocol_version_id),
            details={"naming_standard_id": naming_standard_id},
        )
    )
    await db.flush()
    report.copied.append(
        {**item, "protocol_version_id": str(version.protocol_version_id)}
    )


def _holds(version: ProtocolVersion, rule: FilenameStandardRule) -> bool:
    stored = version.rules.get("filename_standard")
    return stored is not None and FilenameStandardRule.model_validate(stored) == rule
