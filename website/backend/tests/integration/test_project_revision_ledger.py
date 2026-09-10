"""PostgreSQL guarantees for the accepted project revision ledger."""

import hashlib
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import delete, select, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.model.project_revision import ProjectRevision, ProjectRevisionEaf
from app.service.project_revision import (
    append_project_revision,
    verify_project_revision_manifest,
)

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


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
    delayed_first_retry = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="a" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    await session.commit()

    assert retried.revision_id == first.revision_id
    assert delayed_first_retry.revision_id == first.revision_id
    assert (first.ordinal, second.ordinal) == (1, 2)
    assert second.parent_git_commit == first.git_commit
    await session.refresh(project)
    assert project.current_revision_id == second.revision_id


@pytest.mark.asyncio
async def test_current_revision_pointer_cannot_cross_projects(
    session: AsyncSession,
) -> None:
    first_project = await _project(session)
    first_revision = await append_project_revision(
        session,
        project_id=first_project.project_id,
        git_commit="1" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    second_project = Project(
        project_name="other-revision-ledger",
        project_path="other-revision-ledger",
        instance_id=first_project.instance_id,
    )
    session.add(second_project)
    await session.flush()

    second_project.current_revision_id = first_revision.revision_id
    with pytest.raises(DBAPIError):
        await session.commit()
    await session.rollback()


@pytest.mark.asyncio
async def test_revision_captures_exact_eaf_manifest(session: AsyncSession) -> None:
    project = await _project(session)
    raw_xml = EAF_FIXTURE.read_bytes()
    digest = hashlib.sha256(raw_xml).hexdigest()
    content = FileContent(
        filename="session.eaf",
        file_size=len(raw_xml),
        content_hash=digest,
        user_id=None,
    )
    elan_file = ElanFile(
        file_content=content,
        project=project,
        filename="session.eaf",
        file_path="revision-ledger/elan_files/session.eaf",
        last_modified=datetime.now(),
    )
    session.add_all([content, elan_file])
    await session.flush()
    eaf_revision = EafRevision(
        elan_id=elan_file.elan_id,
        revision_number=1,
        sha256=digest,
        raw_xml=raw_xml,
        created_by=None,
    )
    session.add(eaf_revision)
    await session.flush()

    revision = await append_project_revision(
        session,
        project_id=project.project_id,
        git_commit="e" * 40,
        parent_git_commit=None,
        source_type="migration",
        actor_user_id=None,
    )
    project_revision_id = revision.revision_id
    eaf_revision_id = eaf_revision.revision_id
    manifest_sha256 = revision.manifest_sha256
    await session.commit()

    manifest = await session.scalar(
        select(ProjectRevisionEaf).where(
            ProjectRevisionEaf.project_revision_id == project_revision_id
        )
    )
    assert manifest is not None
    assert manifest.filename == "session.eaf"
    assert manifest.eaf_revision_id == eaf_revision_id
    assert manifest.sha256 == digest
    assert manifest.parser_version == "1"
    assert len(manifest.structured_projection["tiers"]) == 2
    assert len(manifest.structured_projection["controlled_vocabularies"]) == 1
    assert manifest_sha256 is not None
    await verify_project_revision_manifest(session, project_revision_id)

    with pytest.raises(DBAPIError) as error:
        await session.execute(
            update(ProjectRevisionEaf)
            .where(
                ProjectRevisionEaf.project_revision_id == project_revision_id,
                ProjectRevisionEaf.filename == "session.eaf",
            )
            .values(sha256="f" * 64)
        )
        await session.commit()
    assert "PROJECT_REVISION_EAF is append-only" in str(error.value.orig)
    await session.rollback()
    await verify_project_revision_manifest(session, project_revision_id)


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
