"""Real PostgreSQL scenarios for durable contribution reviews."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.pending_upload import get_pending_uploads, save_pending_upload
from app.model.association import UserToProject
from app.model.audit_event import AuditEvent
from app.model.enums import (
    ProjectPermission,
    ReviewCaseState,
    Severity,
    Status,
    Type,
    UserRole,
)
from app.model.instance import Instance
from app.model.notification import Notification
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.user import User
from app.schema.review import (
    ReviewCaseCreate,
    ReviewCaseTransition,
    ReviewCommentCreate,
)
from app.service.review import add_comment, create_case, transition_case


def _user(username: str, instance: Instance, role: UserRole = UserRole.PUBLIC) -> User:
    return User(
        username=username,
        email=f"{username}@example.org",
        hashed_password="unused-test-value",  # noqa: S106
        first_name=username.title(),
        last_name="Researcher",
        affiliation=instance.institution_name,
        department="Linguistics",
        activation_code="fixture",
        instance=instance,
        role=role,
    )


@pytest.mark.asyncio
async def test_review_case_discussion_assignment_and_resubmission_are_audited(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Research",
        institution_name="Research Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    reviewer = _user("reviewer", institution, UserRole.ADMIN)
    contributor = _user("contributor", institution)
    project = Project(
        project_name="Corpus",
        project_path="corpus",
        instance=institution,
    )
    session.add_all([institution, reviewer, contributor, project])
    await session.flush()
    session.add(
        UserToProject(
            project_id=project.project_id,
            user_id=contributor.user_id,
            permission=ProjectPermission.WRITE,
        )
    )
    first_upload = PendingUpload(
        upload_type=Type.PENDING_UPLOAD,
        upload_description="First submission",
        severity=Severity.LOW,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="first-submission",
        project_id=project.project_id,
    )
    second_upload = PendingUpload(
        upload_type=Type.PENDING_UPLOAD,
        upload_description="Corrected submission",
        severity=Severity.LOW,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="corrected-submission",
        project_id=project.project_id,
    )
    session.add_all([first_upload, second_upload])
    await session.commit()

    created = await create_case(
        session,
        project.project_id,
        reviewer.user_id,
        ReviewCaseCreate(
            upload_id=first_upload.upload_id,
            title="Check right-hand gloss",
            filename="session.eaf",
            tier_id="Gloss-RH",
            annotation_id="a42",
            start_ms=134_200,
            end_ms=135_000,
            initial_comment="Please verify this value against the protocol.",
        ),
    )
    assert created.state == ReviewCaseState.OPEN
    assert created.assigned_to == reviewer.user_id
    assert created.assignee_name == "Reviewer Researcher"
    assert created.comments[0].body.startswith("Please verify")

    discussed = await add_comment(
        session,
        project.project_id,
        created.case_id,
        contributor.user_id,
        ReviewCommentCreate(body="I will correct this in ELAN."),
    )
    assert [comment.author_name for comment in discussed.comments] == [
        "Reviewer Researcher",
        "Contributor Researcher",
    ]

    requested = await transition_case(
        session,
        project.project_id,
        created.case_id,
        reviewer.user_id,
        ReviewCaseTransition(
            state=ReviewCaseState.CHANGES_REQUESTED,
            assigned_to=contributor.user_id,
        ),
    )
    assert requested.assignee_name == "Contributor Researcher"

    resubmitted = await transition_case(
        session,
        project.project_id,
        created.case_id,
        reviewer.user_id,
        ReviewCaseTransition(
            state=ReviewCaseState.RESUBMITTED,
            assigned_to=contributor.user_id,
            resubmitted_upload_id=second_upload.upload_id,
        ),
    )
    assert resubmitted.resubmitted_upload_id == second_upload.upload_id
    assert resubmitted.resolved_at is None
    notifications = (
        await session.scalars(
            select(Notification).where(
                Notification.user_id.in_([reviewer.user_id, contributor.user_id])
            )
        )
    ).all()
    assert {notification.title for notification in notifications} == {
        "New review comment",
        "Review assigned to you",
    }
    audit_count = await session.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(AuditEvent.resource_id == str(created.case_id))
    )
    assert audit_count == 4


@pytest.mark.asyncio
async def test_review_rejects_cross_project_submission_and_invalid_transition(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Boundary",
        institution_name="Boundary Institute",
        contact_email="admin@boundary.example",
        domain="boundary.example",
        timezone="UTC",
    )
    admin = _user("admin", institution, UserRole.ADMIN)
    first = Project(project_name="First", project_path="first", instance=institution)
    second = Project(project_name="Second", project_path="second", instance=institution)
    session.add_all([institution, admin, first, second])
    await session.flush()
    upload = PendingUpload(
        upload_type=Type.PENDING_UPLOAD,
        upload_description="Second project upload",
        severity=Severity.LOW,
        status=Status.PENDING_ADMIN_APPROVAL,
        branch_name="submission",
        project_id=second.project_id,
    )
    session.add(upload)
    await session.commit()

    with pytest.raises(ValueError, match="does not belong"):
        await create_case(
            session,
            first.project_id,
            admin.user_id,
            ReviewCaseCreate(upload_id=upload.upload_id, title="Wrong project"),
        )

    valid = await create_case(
        session,
        second.project_id,
        admin.user_id,
        ReviewCaseCreate(upload_id=upload.upload_id, title="Valid case"),
    )
    await transition_case(
        session,
        second.project_id,
        valid.case_id,
        admin.user_id,
        ReviewCaseTransition(state=ReviewCaseState.CLOSED),
    )
    with pytest.raises(ValueError, match="Cannot move"):
        await transition_case(
            session,
            second.project_id,
            valid.case_id,
            admin.user_id,
            ReviewCaseTransition(state=ReviewCaseState.RESOLVED),
        )
    reopened = await transition_case(
        session,
        second.project_id,
        valid.case_id,
        admin.user_id,
        ReviewCaseTransition(state=ReviewCaseState.OPEN),
    )
    assert reopened.state == ReviewCaseState.OPEN
    assert reopened.resolved_at is None

    direct_correction = await create_case(
        session,
        second.project_id,
        admin.user_id,
        ReviewCaseCreate(
            upload_id=upload.upload_id,
            request_changes=True,
            title="Correct the submitted annotation",
        ),
    )
    assert direct_correction.state == ReviewCaseState.CHANGES_REQUESTED


@pytest.mark.asyncio
async def test_contribution_queue_retains_provenance_and_excludes_resolved_work(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="Provenance",
        institution_name="Provenance Institute",
        contact_email="admin@provenance.example",
        domain="provenance.example",
        timezone="UTC",
    )
    contributor = _user("provenance-contributor", institution)
    project = Project(
        project_name="Provenance corpus",
        project_path="provenance-corpus",
        instance=institution,
    )
    session.add_all([institution, contributor, project])
    await session.flush()

    pending = await save_pending_upload(
        session,
        project.project_id,
        "submission-pending",
        {"upload_data": {"new_files": ["session.eaf"]}},
        submitted_by=contributor.user_id,
        base_commit="a" * 40,
    )
    newer_pending = await save_pending_upload(
        session,
        project.project_id,
        "submission-newer-pending",
        {"upload_data": {"new_files": ["later-session.eaf"]}},
        submitted_by=contributor.user_id,
        base_commit="d" * 40,
    )
    resolved = PendingUpload(
        upload_type=Type.PENDING_UPLOAD,
        upload_description="Already accepted",
        severity=Severity.LOW,
        status=Status.RESOLVED,
        branch_name="submission-resolved",
        project_id=project.project_id,
        submitted_by=contributor.user_id,
        base_commit="b" * 40,
        accepted_commit="c" * 40,
    )
    session.add(resolved)
    await session.commit()

    queue = await get_pending_uploads(session, project.project_id)

    assert [item.upload_id for item in queue] == [
        newer_pending.upload_id,
        pending.upload_id,
    ]
    assert queue[0].submitted_by == contributor.user_id
    assert queue[0].base_commit == "d" * 40
