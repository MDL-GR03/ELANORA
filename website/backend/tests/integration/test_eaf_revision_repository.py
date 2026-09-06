"""Database-backed tests for immutable EAF revision storage."""

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import app.model  # noqa: F401 - register complete metadata
from app.crud.eaf_ingestion_attempt import record_rejected_eaf
from app.crud.eaf_revision import append_eaf_revision
from app.crud.project import delete_project_db, get_project_by_name, restore_project_db
from app.elan import ValidationIssue, parse_eaf
from app.model.eaf_ingestion_attempt import EafIngestionAttempt
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.model.user import User, UserRole

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


async def _stored_elan_file(
    session: AsyncSession, sha256: str
) -> tuple[ElanFile, User]:
    instance = Instance(
        instance_name="Research",
        institution_name="Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    user = User(
        username="researcher",
        email="researcher@example.org",
        hashed_password="not-used-in-this-test",  # noqa: S106 - inert fixture
        first_name="Ada",
        last_name="Researcher",
        affiliation="Institute",
        department="Linguistics",
        activation_code="fixture",
        instance=instance,
        role=UserRole.ADMIN,
    )
    session.add_all([instance, user])
    await session.flush()
    project = Project(
        project_name="Corpus",
        description="Integration fixture",
        instance_id=instance.instance_id,
        project_path="Corpus",
    )
    content = FileContent(
        filename="complete-valid.eaf",
        file_size=FIXTURE.stat().st_size,
        content_hash=sha256,
        user_id=user.user_id,
    )
    session.add_all([project, content])
    await session.flush()
    elan_file = ElanFile(
        content_id=content.content_id,
        project_id=project.project_id,
        filename="complete-valid.eaf",
        file_path="Corpus/elan_files/complete-valid.eaf",
        last_modified=content.created_at,
    )
    session.add(elan_file)
    await session.flush()
    return elan_file, user


@pytest.mark.asyncio
async def test_revisions_are_lossless_ordered_and_idempotent(
    session: AsyncSession,
) -> None:
    """Store exact valid EAF bytes while deduplicating identical imports."""
    first_document = parse_eaf(FIXTURE.read_bytes())
    elan_file, user = await _stored_elan_file(session, first_document.sha256)

    first = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=first_document.sha256,
        raw_xml=first_document.raw_xml,
        created_by=user.user_id,
    )
    duplicate = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=first_document.sha256,
        raw_xml=first_document.raw_xml,
        created_by=user.user_id,
    )
    changed_document = parse_eaf(first_document.raw_xml.replace(b"A01", b"A03", 1))
    second = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=changed_document.sha256,
        raw_xml=changed_document.raw_xml,
        created_by=user.user_id,
    )

    revisions = list(
        (
            await session.execute(
                select(EafRevision)
                .where(EafRevision.elan_id == elan_file.elan_id)
                .order_by(EafRevision.revision_number)
            )
        )
        .scalars()
        .all()
    )
    assert duplicate.revision_id == first.revision_id
    assert [revision.revision_number for revision in revisions] == [1, 2]
    assert revisions[0].raw_xml == FIXTURE.read_bytes()
    assert revisions[1].raw_xml == changed_document.raw_xml
    assert second.revision_number == 2


@pytest.mark.asyncio
async def test_normal_project_deletion_preserves_research_history(
    session: AsyncSession,
) -> None:
    """A UI deletion tombstones a project without cascading EAF source bytes."""
    document = parse_eaf(FIXTURE.read_bytes())
    elan_file, user = await _stored_elan_file(session, document.sha256)
    revision = await append_eaf_revision(
        session,
        elan_id=elan_file.elan_id,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        created_by=user.user_id,
    )

    await delete_project_db(session, "Corpus")

    project = await session.get(Project, elan_file.project_id)
    stored_revision = await session.get(EafRevision, revision.revision_id)
    assert project is not None and project.deleted_at is not None
    assert stored_revision is not None
    assert stored_revision.raw_xml == FIXTURE.read_bytes()
    assert await get_project_by_name(session, "Corpus") is None

    restored = await restore_project_db(session, "Corpus")
    assert restored.deleted_at is None
    assert (await get_project_by_name(session, "Corpus")) is restored


@pytest.mark.asyncio
async def test_rejected_ingestion_preserves_original_bytes_and_issues(
    session: AsyncSession,
) -> None:
    """Keep a rejected source recoverable without creating an EAF revision."""
    valid_document = parse_eaf(FIXTURE.read_bytes())
    elan_file, user = await _stored_elan_file(session, valid_document.sha256)
    invalid = b"<ANNOTATION_DOCUMENT>"
    issue = ValidationIssue(
        code="xml_syntax", message="XML is not well formed", location="line 1"
    )

    attempt = record_rejected_eaf(
        session,
        instance_id=user.instance_id,
        project_id=elan_file.project_id,
        requested_project_name="Corpus",
        filename="unfinished.eaf",
        raw_xml=invalid,
        issues=(issue,),
        submitted_by=user.user_id,
    )
    await session.commit()

    stored = await session.get(EafIngestionAttempt, attempt.attempt_id)
    assert stored is not None
    assert stored.raw_xml == invalid
    assert (
        stored.sha256
        == "ff3e7e090b4340d524ade9f2c5cbda0a24383110e667a92059a56ece38375373"
    )
    assert stored.validation_issues == [
        {
            "code": "xml_syntax",
            "message": "XML is not well formed",
            "location": "line 1",
        }
    ]
    assert (
        await session.scalar(
            select(EafRevision).where(EafRevision.sha256 == stored.sha256)
        )
        is None
    )
