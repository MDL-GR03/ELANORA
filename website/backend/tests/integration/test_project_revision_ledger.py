"""PostgreSQL guarantees for the accepted project revision ledger."""

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.instance import Instance
from app.model.project import Project
from app.model.project_revision import ProjectRevision
from app.service.project_revision import append_project_revision


async def _project(session: AsyncSession) -> Project:
    institution = Instance(
        instance_name="revision-ledger-instance",
        institution_name="Revision Ledger Institute",
        contact_email="admin@revision-ledger.example",
        domain="revision-ledger.example",
        timezone="UTC",
    )
    project = Project(
        project_name="revision-ledger",
        project_path="revision-ledger",
        instance=institution,
    )
    session.add_all([institution, project])
    await session.flush()
    return project


@pytest.mark.asyncio
async def test_revision_append_is_ordered_and_retry_safe(
    session: AsyncSession,
) -> None:
    project = await _project(session)
    first = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="a" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    retried = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="a" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    second = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="b" * 40,
        parent_git_commit=first.git_commit,
        source_type="restoration",
        actor_user_id=None,
    )
    await session.commit()

    assert retried.revision_id == first.revision_id
    assert (first.ordinal, second.ordinal) == (1, 2)
    assert second.parent_git_commit == first.git_commit


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["update", "delete"])
async def test_revision_rows_cannot_be_changed_or_deleted(
    session: AsyncSession, mutation: str
) -> None:
    project = await _project(session)
    revision = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="c" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    revision_id = revision.revision_id
    await session.commit()

    statement = (
        update(ProjectRevision)
        .where(ProjectRevision.revision_id == revision_id)
        .values(git_commit="d" * 40)
        if mutation == "update"
        else delete(ProjectRevision).where(ProjectRevision.revision_id == revision_id)
    )
    with pytest.raises(DBAPIError) as error:
        await session.execute(statement)
        await session.commit()
    assert "PROJECT_REVISION is append-only" in str(error.value.orig)
    await session.rollback()

    retained = await session.scalar(
        select(ProjectRevision).where(ProjectRevision.revision_id == revision_id)
    )
    assert retained is not None
