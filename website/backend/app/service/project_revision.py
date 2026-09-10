"""Append-only operations for the accepted project revision ledger."""

import hashlib
import json
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.elan.parser import parse_eaf
from app.elan.projection import EAF_PROJECTION_VERSION, document_projection
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.project import Project
from app.model.project_revision import ProjectRevision, ProjectRevisionEaf

RevisionSource = Literal["contribution", "restoration", "migration"]


async def _current_eaf_manifest(
    db: AsyncSession, project_id: int
) -> list[tuple[str, EafRevision]]:
    """Return the current projection's exact immutable source revisions."""
    latest_number = (
        select(
            EafRevision.elan_id,
            func.max(EafRevision.revision_number).label("revision_number"),
        )
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project_id)
        .group_by(EafRevision.elan_id)
        .subquery()
    )
    rows = (
        await db.execute(
            select(ElanFile.filename, EafRevision)
            .join(latest_number, latest_number.c.elan_id == ElanFile.elan_id)
            .join(
                EafRevision,
                (EafRevision.elan_id == latest_number.c.elan_id)
                & (EafRevision.revision_number == latest_number.c.revision_number),
            )
            .where(ElanFile.project_id == project_id)
            .order_by(ElanFile.filename)
        )
    ).all()
    projected_count = await db.scalar(
        select(func.count())
        .select_from(ElanFile)
        .where(ElanFile.project_id == project_id)
    )
    if len(rows) != (projected_count or 0):
        raise RuntimeError("Every projected EAF must have an immutable source revision")
    return [(filename, revision) for filename, revision in rows]


def _manifest_checksum(entries: list[tuple[str, EafRevision]]) -> str:
    canonical = json.dumps(
        [
            {"filename": filename, "sha256": revision.sha256}
            for filename, revision in entries
        ],
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def verify_project_revision_manifest(
    db: AsyncSession, revision_id: object
) -> list[ProjectRevisionEaf]:
    """Raise when a stored manifest no longer matches its immutable EAF bytes."""
    revision = await db.get(ProjectRevision, revision_id)
    if revision is None:
        raise ValueError("Project revision not found")
    manifest = list(
        (
            await db.scalars(
                select(ProjectRevisionEaf)
                .where(ProjectRevisionEaf.project_revision_id == revision.revision_id)
                .order_by(ProjectRevisionEaf.filename)
            )
        ).all()
    )
    canonical_entries: list[dict[str, str]] = []
    for manifest_entry in manifest:
        actual_sha256 = hashlib.sha256(manifest_entry.raw_xml).hexdigest()
        if actual_sha256 != manifest_entry.sha256:
            raise RuntimeError(
                f"EAF revision checksum mismatch for {manifest_entry.filename}"
            )
        canonical_entries.append(
            {"filename": manifest_entry.filename, "sha256": manifest_entry.sha256}
        )
    checksum = hashlib.sha256(
        json.dumps(
            canonical_entries,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
    ).hexdigest()
    if revision.manifest_sha256 != checksum:
        raise RuntimeError("Project revision manifest checksum mismatch")
    return manifest


async def append_project_revision(
    db: AsyncSession,
    *,
    project_id: int,
    git_commit: str,
    parent_git_commit: str | None,
    source_type: RevisionSource,
    actor_user_id: int | None,
    contribution_id: int | None = None,
    details: dict[str, object] | None = None,
) -> ProjectRevision:
    """Append one revision while serializing ordinals on the project row."""
    project = await db.scalar(
        select(Project).where(Project.project_id == project_id).with_for_update()
    )
    if project is None:
        raise ValueError("Project not found")
    manifest = await _current_eaf_manifest(db, project_id)
    manifest_sha256 = _manifest_checksum(manifest)
    existing = await db.scalar(
        select(ProjectRevision).where(
            ProjectRevision.project_id == project_id,
            ProjectRevision.git_commit == git_commit,
        )
    )
    if existing is not None:
        if existing.manifest_sha256 != manifest_sha256:
            raise RuntimeError("Existing project revision has a different EAF manifest")
        return existing
    latest = await db.scalar(
        select(func.max(ProjectRevision.ordinal)).where(
            ProjectRevision.project_id == project_id
        )
    )
    revision = ProjectRevision(
        project_id=project_id,
        ordinal=(latest or 0) + 1,
        git_commit=git_commit,
        parent_git_commit=parent_git_commit,
        manifest_sha256=manifest_sha256,
        source_type=source_type,
        contribution_id=contribution_id,
        actor_user_id=actor_user_id,
        details=details or {},
    )
    db.add(revision)
    await db.flush()
    db.add_all(
        [
            ProjectRevisionEaf(
                project_revision_id=revision.revision_id,
                filename=filename,
                eaf_revision_id=eaf_revision.revision_id,
                sha256=eaf_revision.sha256,
                raw_xml=eaf_revision.raw_xml,
                parser_version=EAF_PROJECTION_VERSION,
                structured_projection=document_projection(
                    parse_eaf(eaf_revision.raw_xml)
                ),
            )
            for filename, eaf_revision in manifest
        ]
    )
    await db.flush()
    return revision
