"""Database enforcement for project-scoped workflow relationships."""

from datetime import UTC, datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.contribution_change_set import ContributionChangeSet
from app.model.enums import Severity, Status, Type
from app.model.instance import Instance
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.model.project_revision import ProjectRevision
from app.model.review import ReviewCase


async def _projects_and_uploads(
    session: AsyncSession,
) -> tuple[Project, Project, PendingUpload, PendingUpload]:
    instance = Instance(
        instance_name="Ownership constraints",
        institution_name="Research institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    first_project = Project(
        project_name="First corpus",
        project_path="first-corpus",
        instance=instance,
    )
    second_project = Project(
        project_name="Second corpus",
        project_path="second-corpus",
        instance=instance,
    )
    session.add_all([instance, first_project, second_project])
    await session.flush()
    first_upload = PendingUpload(
        upload_type=Type.UPLOAD_WITH_MODIFICATIONS,
        upload_description="First contribution",
        severity=Severity.LOW,
        status=Status.READY_TO_MERGE,
        project_id=first_project.project_id,
    )
    second_upload = PendingUpload(
        upload_type=Type.UPLOAD_WITH_MODIFICATIONS,
        upload_description="Second contribution",
        severity=Severity.LOW,
        status=Status.READY_TO_MERGE,
        project_id=second_project.project_id,
    )
    session.add_all([first_upload, second_upload])
    await session.flush()
    return first_project, second_project, first_upload, second_upload


@pytest.mark.asyncio
async def test_change_set_cannot_link_another_projects_upload(
    session: AsyncSession,
) -> None:
    first_project, _, _, second_upload = await _projects_and_uploads(session)
    session.add(
        ContributionChangeSet(
            project_id=first_project.project_id,
            upload_id=second_upload.upload_id,
            branch_name="contribution/second",
            resolution_strategy="auto",
            expected_commit="a" * 40,
            state="queued",
            attempts=0,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_review_case_cannot_link_another_projects_upload(
    session: AsyncSession,
) -> None:
    first_project, _, _, second_upload = await _projects_and_uploads(session)
    session.add(
        ReviewCase(
            project_id=first_project.project_id,
            upload_id=second_upload.upload_id,
            title="Cross-project review",
            state="open",
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_review_case_cannot_link_another_projects_resubmission(
    session: AsyncSession,
) -> None:
    first_project, _, first_upload, second_upload = await _projects_and_uploads(session)
    session.add(
        ReviewCase(
            project_id=first_project.project_id,
            upload_id=first_upload.upload_id,
            resubmitted_upload_id=second_upload.upload_id,
            title="Cross-project resubmission",
            state="resubmitted",
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_project_revision_cannot_link_another_projects_contribution(
    session: AsyncSession,
) -> None:
    first_project, _, _, second_upload = await _projects_and_uploads(session)
    session.add(
        ProjectRevision(
            project_id=first_project.project_id,
            ordinal=1,
            git_commit="b" * 40,
            source_type="contribution",
            contribution_id=second_upload.upload_id,
            details={},
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_integrity_status_cannot_link_another_projects_revision(
    session: AsyncSession,
) -> None:
    first_project, second_project, _, _ = await _projects_and_uploads(session)
    revision = ProjectRevision(
        project_id=second_project.project_id,
        ordinal=1,
        git_commit="c" * 40,
        source_type="migration",
        details={},
    )
    session.add(revision)
    await session.flush()
    session.add(
        ProjectIntegrityStatus(
            project_id=first_project.project_id,
            revision_id=revision.revision_id,
            status="healthy",
            details={},
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_same_project_workflow_links_remain_valid(session: AsyncSession) -> None:
    first_project, _, first_upload, _ = await _projects_and_uploads(session)
    revision = ProjectRevision(
        project_id=first_project.project_id,
        ordinal=1,
        git_commit="d" * 40,
        source_type="contribution",
        contribution_id=first_upload.upload_id,
        details={},
    )
    session.add_all(
        [
            ContributionChangeSet(
                project_id=first_project.project_id,
                upload_id=first_upload.upload_id,
                branch_name="contribution/first",
                resolution_strategy="auto",
                expected_commit="d" * 40,
                state="queued",
                attempts=0,
            ),
            ReviewCase(
                project_id=first_project.project_id,
                upload_id=first_upload.upload_id,
                resubmitted_upload_id=first_upload.upload_id,
                title="Valid review",
                state="resubmitted",
            ),
            revision,
        ]
    )
    await session.flush()
    session.add(
        ProjectIntegrityStatus(
            project_id=first_project.project_id,
            revision_id=revision.revision_id,
            status="healthy",
            details={"checked_at": datetime.now(UTC).isoformat()},
        )
    )

    await session.flush()
