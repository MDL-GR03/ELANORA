"""End-to-end contribution decisions using PostgreSQL and real Git history."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.elan_file import get_elan_files_by_project
from app.crud.pending_upload import get_pending_uploads, save_pending_upload
from app.model.enums import Status, UserRole
from app.model.instance import Instance
from app.model.project import Project
from app.model.project_revision import ProjectRevision
from app.model.user import User
from app.service.elan import ElanService
from app.service.git import GitService
from app.service.git_operations import GitCommandRunner
from app.service.project_revision import verify_project_revision_manifest

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


@pytest.fixture(autouse=True)
def isolate_recovery_backups(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep merge workflow tests inside tmp_path; backup behavior is independent."""
    monkeypatch.setattr("app.service.git.update_backup", lambda *_args: None)
    monkeypatch.setattr("app.service.git_operations.update_backup", lambda *_args: None)


def _user(username: str, instance: Instance, role: UserRole = UserRole.PUBLIC) -> User:
    return User(
        username=username,
        email=f"{username}@workflow.example",
        hashed_password="unused-test-value",  # noqa: S106
        first_name=username.title(),
        last_name="Researcher",
        affiliation=instance.institution_name,
        department="Linguistics",
        activation_code="fixture",
        instance=instance,
        role=role,
    )


async def _domain(
    session: AsyncSession, tmp_path: Path, project_name: str
) -> tuple[Project, User, User, User, Path, GitCommandRunner]:
    institution = Instance(
        instance_name=f"{project_name}-institution",
        institution_name="Workflow Institute",
        contact_email=f"admin@{project_name}.example",
        domain=f"{project_name}.example",
        timezone="UTC",
    )
    admin = _user(f"{project_name}-admin", institution, UserRole.ADMIN)
    researcher_a = _user(f"{project_name}-researcher-a", institution)
    researcher_b = _user(f"{project_name}-researcher-b", institution)
    project = Project(
        project_name=project_name,
        project_path=project_name,
        instance=institution,
    )
    session.add_all([institution, admin, researcher_a, researcher_b, project])
    await session.flush()

    project_path = tmp_path / project_name
    (project_path / "elan_files").mkdir(parents=True)
    baseline = EAF_FIXTURE.read_bytes()
    (project_path / "elan_files" / "video-11.eaf").write_bytes(baseline)
    (project_path / "elan_files" / "session-12.eaf").write_bytes(baseline)
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA workflow test"], check=True)
    runner.run(["config", "user.email", "workflow-test@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Accepted subject baselines"], check=True)
    return project, admin, researcher_a, researcher_b, project_path, runner


def _branch_with_changes(
    runner: GitCommandRunner,
    project_path: Path,
    branch_name: str,
    changes: dict[str, tuple[bytes, bytes]],
) -> None:
    runner.run(["checkout", "master"], check=True)
    runner.run(["checkout", "-b", branch_name], check=True)
    for filename, (before, after) in changes.items():
        target = project_path / "elan_files" / filename
        target.write_bytes(target.read_bytes().replace(before, after))
    runner.run(["add", "elan_files"], check=True)
    runner.run(["commit", "-m", branch_name], check=True)
    runner.run(["checkout", "master"], check=True)


async def _pending(
    session: AsyncSession,
    project: Project,
    user: User,
    runner: GitCommandRunner,
    branch_name: str,
    filenames: list[str],
):
    return await save_pending_upload(
        session,
        project.project_id,
        branch_name,
        {
            "uploaded_by": user.username,
            "modified_files": [f"elan_files/{name}" for name in filenames],
            "modified_files_count": len(filenames),
        },
        submitted_by=user.user_id,
        base_commit=runner.run(["rev-parse", "master"], check=True).stdout.strip(),
    )


@pytest.mark.asyncio
async def test_two_researchers_can_merge_different_subjects_from_same_baseline(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, admin, researcher_a, researcher_b, project_path, runner = await _domain(
        session, tmp_path, "parallel-subjects"
    )
    _branch_with_changes(
        runner,
        project_path,
        "researcher-a-video-11",
        {
            "video-11.eaf": (
                b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
                b"<ANNOTATION_VALUE>Researcher A video 11</ANNOTATION_VALUE>",
            )
        },
    )
    _branch_with_changes(
        runner,
        project_path,
        "researcher-b-session-12",
        {
            "session-12.eaf": (
                b"<ANNOTATION_VALUE>Bonjour</ANNOTATION_VALUE>",
                b"<ANNOTATION_VALUE>Researcher B session 12</ANNOTATION_VALUE>",
            )
        },
    )
    upload_a = await _pending(
        session,
        project,
        researcher_a,
        runner,
        "researcher-a-video-11",
        ["video-11.eaf"],
    )
    upload_b = await _pending(
        session,
        project,
        researcher_b,
        runner,
        "researcher-b-session-12",
        ["session-12.eaf"],
    )
    service = GitService(base_path=str(tmp_path))

    initial = await service.get_pending_uploads_with_status(
        project.project_name, session
    )
    assert {item["merge_status"] for item in initial["pending_uploads"]} == {
        "ready_to_merge"
    }

    await service.complete_pending_upload(
        project.project_name,
        upload_a.branch_name,
        "auto",
        session,
        admin.user_id,
    )
    after_first = await service.get_pending_uploads_with_status(
        project.project_name, session
    )
    assert after_first["total_pending"] == 1
    assert after_first["pending_uploads"][0]["upload_id"] == upload_b.upload_id
    assert after_first["pending_uploads"][0]["merge_status"] == "ready_to_merge"

    await service.complete_pending_upload(
        project.project_name,
        upload_b.branch_name,
        "auto",
        session,
        admin.user_id,
    )
    await session.refresh(upload_a)
    await session.refresh(upload_b)
    assert upload_a.status == Status.RESOLVED
    assert upload_b.status == Status.RESOLVED
    assert await get_pending_uploads(session, project.project_id) == []
    revisions = list(
        (
            await session.scalars(
                select(ProjectRevision)
                .where(ProjectRevision.project_id == project.project_id)
                .order_by(ProjectRevision.ordinal)
            )
        ).all()
    )
    assert [revision.ordinal for revision in revisions] == [1, 2]
    assert [revision.contribution_id for revision in revisions] == [
        upload_a.upload_id,
        upload_b.upload_id,
    ]
    assert revisions[1].parent_git_commit == revisions[0].git_commit
    current_revision_id = revisions[1].revision_id
    project_name = project.project_name
    admin_id = admin.user_id
    with pytest.raises(ValueError, match="current accepted"):
        await service.rebuild_current_revision_projection(
            project_name,
            revisions[0].revision_id,
            session,
            admin_id,
        )
    with pytest.raises(ValueError, match="current accepted"):
        await service.recover_current_revision_from_manifest(
            project_name,
            revisions[0].revision_id,
            session,
            admin_id,
        )
    first_rebuild = await service.rebuild_current_revision_projection(
        project_name,
        current_revision_id,
        session,
        admin_id,
    )
    second_rebuild = await service.rebuild_current_revision_projection(
        project_name,
        current_revision_id,
        session,
        admin_id,
    )
    assert first_rebuild["manifest_sha256"] == second_rebuild["manifest_sha256"]
    assert first_rebuild["file_count"] == second_rebuild["file_count"] == 2
    assert (
        b"Researcher A video 11"
        in (project_path / "elan_files" / "video-11.eaf").read_bytes()
    )
    assert (
        b"Researcher B session 12"
        in (project_path / "elan_files" / "session-12.eaf").read_bytes()
    )

    manifest = await verify_project_revision_manifest(session, current_revision_id)
    expected_bytes = {entry.filename: entry.raw_xml for entry in manifest}
    (project_path / "elan_files" / "video-11.eaf").write_bytes(b"damaged")
    (project_path / "elan_files" / "session-12.eaf").unlink()
    (project_path / "elan_files" / "unexpected.eaf").write_bytes(
        EAF_FIXTURE.read_bytes()
    )
    elan_service = ElanService(session)
    for elan_file, _username in await get_elan_files_by_project(
        session, project.project_id
    ):
        assert await elan_service.delete_elan_files_from_db(
            elan_file.filename, project.project_name, commit_changes=False
        )
    await session.commit()

    with (
        patch.object(
            service,
            "rebuild_current_revision_projection",
            AsyncMock(side_effect=RuntimeError("simulated rebuild failure")),
        ),
        pytest.raises(RuntimeError, match="simulated rebuild failure"),
    ):
        await service.recover_current_revision_from_manifest(
            project_name,
            current_revision_id,
            session,
            admin_id,
        )
    assert (project_path / "elan_files" / "video-11.eaf").read_bytes() == b"damaged"
    assert not (project_path / "elan_files" / "session-12.eaf").exists()
    assert (project_path / "elan_files" / "unexpected.eaf").exists()

    recovered = await service.recover_current_revision_from_manifest(
        project_name,
        current_revision_id,
        session,
        admin_id,
    )
    assert recovered["status"] == "recovered"
    assert recovered["file_count"] == 2
    assert {
        path.name: path.read_bytes()
        for path in (project_path / "elan_files").glob("*.eaf")
    } == expected_bytes
    projected = await get_elan_files_by_project(session, project.project_id)
    assert {elan_file.filename for elan_file, _username in projected} == {
        "video-11.eaf",
        "session-12.eaf",
    }
    assert not runner.run(["status", "--porcelain"], check=True).stdout.strip()


@pytest.mark.asyncio
async def test_failed_database_commit_restores_git_and_keeps_contribution_pending(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, admin, researcher, _, project_path, runner = await _domain(
        session, tmp_path, "failed-acceptance"
    )
    baseline_commit = runner.get_commit_hash()
    original = b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>"
    _branch_with_changes(
        runner,
        project_path,
        "researcher-failed-acceptance",
        {
            "video-11.eaf": (
                original,
                b"<ANNOTATION_VALUE>Must be rolled back</ANNOTATION_VALUE>",
            )
        },
    )
    upload = await _pending(
        session,
        project,
        researcher,
        runner,
        "researcher-failed-acceptance",
        ["video-11.eaf"],
    )
    project_id = project.project_id
    project_name = project.project_name
    upload_id = upload.upload_id
    branch_name = upload.branch_name
    admin_id = admin.user_id
    await session.commit()

    with (
        patch.object(
            session,
            "commit",
            AsyncMock(side_effect=RuntimeError("simulated database commit failure")),
        ),
        pytest.raises(RuntimeError, match="simulated database commit failure"),
    ):
        await GitService(base_path=str(tmp_path)).complete_pending_upload(
            project_name,
            branch_name,
            "auto",
            session,
            admin_id,
        )

    assert runner.get_commit_hash() == baseline_commit
    assert original in (project_path / "elan_files" / "video-11.eaf").read_bytes()
    remaining = await get_pending_uploads(session, project_id)
    assert [item.upload_id for item in remaining] == [upload_id]
    revisions = await session.scalars(
        select(ProjectRevision).where(ProjectRevision.project_id == project_id)
    )
    assert list(revisions) == []
    assert "researcher-failed-acceptance" in {
        branch.lstrip("* ") for branch in runner.get_branches()
    }


@pytest.mark.asyncio
async def test_disjoint_annotations_in_the_same_eaf_remain_independently_mergeable(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, admin, researcher_a, researcher_b, project_path, runner = await _domain(
        session, tmp_path, "parallel-annotations"
    )
    _branch_with_changes(
        runner,
        project_path,
        "researcher-a-hello",
        {
            "video-11.eaf": (
                b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
                b"<ANNOTATION_VALUE>Researcher A greeting</ANNOTATION_VALUE>",
            )
        },
    )
    _branch_with_changes(
        runner,
        project_path,
        "researcher-b-bonjour",
        {
            "video-11.eaf": (
                b"<ANNOTATION_VALUE>Bonjour</ANNOTATION_VALUE>",
                b"<ANNOTATION_VALUE>Researcher B greeting</ANNOTATION_VALUE>",
            )
        },
    )
    upload_a = await _pending(
        session,
        project,
        researcher_a,
        runner,
        "researcher-a-hello",
        ["video-11.eaf"],
    )
    upload_b = await _pending(
        session,
        project,
        researcher_b,
        runner,
        "researcher-b-bonjour",
        ["video-11.eaf"],
    )
    service = GitService(base_path=str(tmp_path))

    before = await service.get_pending_uploads_with_status(
        project.project_name, session
    )
    assert before["ready_count"] == 2
    assert all(not item["annotation_collisions"] for item in before["pending_uploads"])

    await service.complete_pending_upload(
        project.project_name,
        upload_a.branch_name,
        "auto",
        session,
        admin.user_id,
    )
    after_first = await service.get_pending_uploads_with_status(
        project.project_name, session
    )
    assert after_first["pending_uploads"][0]["upload_id"] == upload_b.upload_id
    assert after_first["pending_uploads"][0]["merge_status"] == "ready_to_merge"

    await service.complete_pending_upload(
        project.project_name,
        upload_b.branch_name,
        "auto",
        session,
        admin.user_id,
    )
    accepted = (project_path / "elan_files" / "video-11.eaf").read_bytes()
    assert b"Researcher A greeting" in accepted
    assert b"Researcher B greeting" in accepted


@pytest.mark.asyncio
async def test_accepting_one_same_subject_edit_turns_the_other_into_a_conflict(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, admin, researcher_a, researcher_b, project_path, runner = await _domain(
        session, tmp_path, "same-subject-conflict"
    )
    original = b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>"
    _branch_with_changes(
        runner,
        project_path,
        "researcher-a-video-11",
        {
            "video-11.eaf": (
                original,
                b"<ANNOTATION_VALUE>Researcher A interpretation</ANNOTATION_VALUE>",
            )
        },
    )
    _branch_with_changes(
        runner,
        project_path,
        "researcher-b-video-11",
        {
            "video-11.eaf": (
                original,
                b"<ANNOTATION_VALUE>Researcher B interpretation</ANNOTATION_VALUE>",
            )
        },
    )
    upload_a = await _pending(
        session,
        project,
        researcher_a,
        runner,
        "researcher-a-video-11",
        ["video-11.eaf"],
    )
    upload_b = await _pending(
        session,
        project,
        researcher_b,
        runner,
        "researcher-b-video-11",
        ["video-11.eaf"],
    )
    _branch_with_changes(
        runner,
        project_path,
        "superseded-video-11",
        {
            "video-11.eaf": (
                original,
                b"<ANNOTATION_VALUE>Superseded interpretation</ANNOTATION_VALUE>",
            )
        },
    )
    superseded = await _pending(
        session,
        project,
        researcher_a,
        runner,
        "superseded-video-11",
        ["video-11.eaf"],
    )
    superseded.superseded_by_upload_id = upload_a.upload_id
    await session.commit()
    service = GitService(base_path=str(tmp_path))

    before = await service.get_pending_uploads_with_status(
        project.project_name, session
    )
    assert before["ready_count"] == 2
    by_id = {item["upload_id"]: item for item in before["pending_uploads"]}
    assert by_id[upload_a.upload_id]["annotation_collisions"] == [
        {
            "contribution_id": upload_b.upload_id,
            "annotations": {"elan_files/video-11.eaf": ["a1"]},
        }
    ]
    assert by_id[upload_b.upload_id]["annotation_collisions"] == [
        {
            "contribution_id": upload_a.upload_id,
            "annotations": {"elan_files/video-11.eaf": ["a1"]},
        }
    ]
    assert by_id[superseded.upload_id]["annotation_collisions"] == []
    await service.complete_pending_upload(
        project.project_name,
        upload_b.branch_name,
        "auto",
        session,
        admin.user_id,
    )

    after = await service.get_pending_uploads_with_status(project.project_name, session)
    remaining = next(
        item
        for item in after["pending_uploads"]
        if item["upload_id"] == upload_a.upload_id
    )
    assert remaining["upload_id"] == upload_a.upload_id
    assert remaining["merge_status"] == "needs_resolution"
    assert remaining["conflicted_files"] == ["elan_files/video-11.eaf"]
    archived = next(
        item
        for item in after["pending_uploads"]
        if item["upload_id"] == superseded.upload_id
    )
    assert archived["merge_status"] == "superseded"
    assert archived["annotation_collisions"] == []


@pytest.mark.asyncio
async def test_identical_two_researcher_submissions_are_marked_as_duplicates(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, _, researcher_a, researcher_b, project_path, runner = await _domain(
        session, tmp_path, "duplicate-subject"
    )
    replacement = b"<ANNOTATION_VALUE>Shared interpretation</ANNOTATION_VALUE>"
    for branch_name in ("researcher-a-video-11", "researcher-b-video-11"):
        _branch_with_changes(
            runner,
            project_path,
            branch_name,
            {
                "video-11.eaf": (
                    b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
                    replacement,
                )
            },
        )
    upload_a = await _pending(
        session,
        project,
        researcher_a,
        runner,
        "researcher-a-video-11",
        ["video-11.eaf"],
    )
    upload_b = await _pending(
        session,
        project,
        researcher_b,
        runner,
        "researcher-b-video-11",
        ["video-11.eaf"],
    )

    queue = await GitService(base_path=str(tmp_path)).get_pending_uploads_with_status(
        project.project_name, session
    )
    by_id = {item["upload_id"]: item for item in queue["pending_uploads"]}
    assert by_id[upload_a.upload_id]["merge_status"] == "ready_to_merge"
    assert by_id[upload_b.upload_id]["merge_status"] == "duplicate"
    assert by_id[upload_b.upload_id]["duplicate_of_upload_id"] == upload_a.upload_id
