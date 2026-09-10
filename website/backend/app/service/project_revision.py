"""Append-only operations for the accepted project revision ledger."""

from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.project import Project
from app.model.project_revision import ProjectRevision

RevisionSource = Literal["contribution", "restoration", "migration"]


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
    existing = await db.scalar(
        select(ProjectRevision).where(
            ProjectRevision.project_id == project_id,
            ProjectRevision.git_commit == git_commit,
        )
    )
    if existing is not None:
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
        source_type=source_type,
        contribution_id=contribution_id,
        actor_user_id=actor_user_id,
        details=details or {},
    )
    db.add(revision)
    await db.flush()
    return revision
