"""Researcher submissions: the path from uploaded EAF files to a pending review.

Nothing tested this path end to end, although it is how every contribution
enters a project. These tests pin its behaviour against real Git and
PostgreSQL.
"""

import io
from datetime import datetime
from pathlib import Path

import pytest
from fastapi import UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.elan_file import ElanFile
from app.model.enums import Status, UserRole
from app.model.instance import Instance
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.user import User
from app.service.contribution_intake import (
    ContributionAlreadyCurrentError,
    DuplicatePendingContributionError,
)
from app.service.git import GitService
from app.service.git_operations import GitCommandRunner

EAF_FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
BASELINE = EAF_FIXTURE.read_bytes()
ORIGINAL_VALUE = b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>"
PROTOCOL = {
    "outcome": "not_configured",
    "protocol_version_id": None,
    "rules_sha256": None,
}


@pytest.fixture(autouse=True)
def isolate_backups(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "app.service.contribution_publication.update_backup", lambda *_a: None
    )
    monkeypatch.setattr("app.service.git_operations.update_backup", lambda *_a: None)


def _revised(label: str) -> bytes:
    replaced = BASELINE.replace(
        ORIGINAL_VALUE, f"<ANNOTATION_VALUE>{label}</ANNOTATION_VALUE>".encode()
    )
    assert replaced != BASELINE, "fixture no longer contains the expected value"
    return replaced


def _upload(filename: str, content: bytes) -> UploadFile:
    return UploadFile(file=io.BytesIO(content), filename=filename, size=len(content))


async def _domain(
    session: AsyncSession, tmp_path: Path, name: str
) -> tuple[Project, User, User, Path, GitCommandRunner]:
    institution = Instance(
        instance_name=f"{name}-institution",
        institution_name="Submission Institute",
        contact_email=f"admin@{name}.example",
        domain=f"{name}.example",
        timezone="UTC",
    )
    users = [
        User(
            username=f"{name}-{role}",
            email=f"{role}@{name}.example",
            hashed_password="unused-test-value",  # noqa: S106
            first_name=role.title(),
            last_name="Researcher",
            affiliation="Submission Institute",
            department="Linguistics",
            activation_code="fixture",
            instance=institution,
            role=UserRole.PUBLIC,
        )
        for role in ("ada", "bea")
    ]
    project = Project(project_name=name, project_path=name, instance=institution)
    session.add_all([institution, *users, project])
    await session.commit()

    project_path = tmp_path / name
    (project_path / "elan_files").mkdir(parents=True)
    # Distinct bytes keep these tests about submission; identical content under
    # different names has its own test below.
    (project_path / "elan_files" / "video-11.eaf").write_bytes(BASELINE)
    (project_path / "elan_files" / "session-12.eaf").write_bytes(
        _revised("Session twelve baseline")
    )
    runner = GitCommandRunner(project_path, maintain_backup=False)
    runner.run(["init", "--initial-branch=master"], check=True)
    runner.run(["config", "user.name", "ELANORA submission test"], check=True)
    runner.run(["config", "user.email", "submission@elanora.invalid"], check=True)
    runner.run(["add", "."], check=True)
    runner.run(["commit", "-m", "Accepted baselines"], check=True)
    return project, users[0], users[1], project_path, runner


async def _submit(
    service: GitService,
    session: AsyncSession,
    project: Project,
    user: User,
    files: list[UploadFile],
) -> dict:
    return await service.add_elan_files(
        project.project_id,
        files,
        session,
        user.user_id,
        user.username,
        protocol_validation=PROTOCOL,
    )


def _branches(runner: GitCommandRunner) -> set[str]:
    listing = runner.run(["branch", "--format=%(refname:short)"], check=True)
    return set(listing.stdout.split())


async def _pending_count(session: AsyncSession, project_id: int) -> int:
    return int(
        await session.scalar(
            select(func.count())
            .select_from(PendingUpload)
            .where(
                PendingUpload.project_id == project_id,
                PendingUpload.status == Status.PENDING_ADMIN_APPROVAL,
            )
        )
        or 0
    )


@pytest.mark.asyncio
async def test_a_revised_file_becomes_a_pending_review_without_touching_accepted_work(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, ada, _, project_path, runner = await _domain(session, tmp_path, "revise")
    project_id = project.project_id

    result = await _submit(
        GitService(base_path=str(tmp_path)),
        session,
        project,
        ada,
        [_upload("video-11.eaf", _revised("Revised by Ada"))],
    )

    assert result["status"] == "pending_admin_approval"
    assert result["auto_accepted"] is False
    assert result["branch_name"].endswith("_pending_approval")
    assert result["existing_files_updated"] == 1
    assert result["new_files_added"] == 0
    assert await _pending_count(session, project_id) == 1
    # The administrator decides; the accepted project is unchanged until then.
    assert (
        runner.run(["branch", "--show-current"], check=True).stdout.strip() == "master"
    )
    assert (project_path / "elan_files" / "video-11.eaf").read_bytes() == BASELINE


@pytest.mark.asyncio
async def test_resubmitting_the_accepted_version_is_refused_without_a_leftover_branch(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, ada, _, _, runner = await _domain(session, tmp_path, "unchanged")
    project_id = project.project_id

    with pytest.raises(ContributionAlreadyCurrentError):
        await _submit(
            GitService(base_path=str(tmp_path)),
            session,
            project,
            ada,
            [_upload("video-11.eaf", BASELINE)],
        )

    assert _branches(runner) == {"master"}
    assert await _pending_count(session, project_id) == 0


@pytest.mark.asyncio
async def test_an_identical_second_submission_is_refused_as_a_duplicate(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, ada, bea, _, runner = await _domain(session, tmp_path, "duplicate")
    project_id = project.project_id
    service = GitService(base_path=str(tmp_path))
    revision = _revised("Shared edit")

    first = await _submit(
        service, session, project, ada, [_upload("video-11.eaf", revision)]
    )
    with pytest.raises(DuplicatePendingContributionError):
        await _submit(
            service, session, project, bea, [_upload("video-11.eaf", revision)]
        )

    assert await _pending_count(session, project_id) == 1
    assert _branches(runner) == {"master", first["branch_name"]}


@pytest.mark.asyncio
async def test_counts_describe_the_accepted_project_whatever_is_checked_out(
    session: AsyncSession, tmp_path: Path
) -> None:
    """An existing file means an accepted one, not one on another branch."""
    project, ada, bea, _, runner = await _domain(session, tmp_path, "checkout")
    service = GitService(base_path=str(tmp_path))

    first = await _submit(
        service, session, project, ada, [_upload("extra-13.eaf", _revised("Ada extra"))]
    )
    # An administrator inspects the pending branch in the working tree.
    runner.run(["checkout", first["branch_name"]], check=True)

    second = await _submit(
        service, session, project, bea, [_upload("extra-13.eaf", _revised("Bea extra"))]
    )

    assert second["new_files_added"] == 1
    assert second["existing_files_updated"] == 0


@pytest.mark.asyncio
async def test_new_files_are_accepted_automatically_when_the_project_allows_it(
    session: AsyncSession, tmp_path: Path
) -> None:
    project, ada, _, project_path, _ = await _domain(session, tmp_path, "autoaccept")
    project_id = project.project_id
    project.auto_accept_new_files = True
    await session.commit()

    result = await _submit(
        GitService(base_path=str(tmp_path)),
        session,
        project,
        ada,
        [_upload("extra-13.eaf", _revised("Automatically accepted"))],
    )

    assert result["auto_accepted"] is True
    assert result["status"] == "accepted_automatically"
    assert (project_path / "elan_files" / "extra-13.eaf").exists()
    assert await _pending_count(session, project_id) == 0


@pytest.mark.asyncio
async def test_a_failed_automatic_acceptance_still_reports_the_saved_contribution(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The contribution is saved before acceptance is attempted.

    If publishing it then fails, the researcher must be told it awaits review,
    not handed a server error for a submission that actually succeeded.
    """
    project, ada, _, project_path, _ = await _domain(session, tmp_path, "autofail")
    project_id = project.project_id
    project.auto_accept_new_files = True
    await session.commit()
    service = GitService(base_path=str(tmp_path))

    async def refuse_publication(*_args: object, **_kwargs: object) -> None:
        await session.rollback()
        raise RuntimeError("publication refused")

    monkeypatch.setattr(service.contribution_publication, "publish", refuse_publication)

    result = await _submit(
        service, session, project, ada, [_upload("extra-13.eaf", _revised("Kept"))]
    )

    assert result["auto_accepted"] is False
    assert result["status"] == "pending_admin_approval"
    assert await _pending_count(session, project_id) == 1
    assert not (project_path / "elan_files" / "extra-13.eaf").exists()


@pytest.mark.asyncio
async def test_a_byte_identical_copy_under_a_new_name_can_be_published(
    session: AsyncSession, tmp_path: Path
) -> None:
    """Sessions started from one template can share bytes and remain distinct files."""
    project, ada, _, project_path, runner = await _domain(session, tmp_path, "template")
    project_id, project_name, ada_id = (
        project.project_id,
        project.project_name,
        ada.user_id,
    )
    service = GitService(base_path=str(tmp_path))

    submitted = await _submit(
        service, session, project, ada, [_upload("session-15.eaf", BASELINE)]
    )
    await service.complete_pending_upload(
        project_name, submitted["branch_name"], "auto", session, ada_id
    )

    accepted = runner.run(
        ["ls-tree", "--name-only", "master", "elan_files/"], check=True
    ).stdout.split()
    assert {"elan_files/video-11.eaf", "elan_files/session-15.eaf"} <= set(accepted)
    assert (project_path / "elan_files" / "session-15.eaf").read_bytes() == (
        project_path / "elan_files" / "video-11.eaf"
    ).read_bytes()
    session.expire_all()
    stored = set(
        (
            await session.scalars(
                select(ElanFile.filename).where(ElanFile.project_id == project_id)
            )
        ).all()
    )
    assert {"video-11.eaf", "session-15.eaf"} <= stored


@pytest.mark.asyncio
async def test_two_uploads_in_the_same_second_are_both_kept(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Branch names used to be unique only to the second.

    The second upload then failed to rename its branch onto the first one's,
    and the failure cleanup deleted the first contribution's branch.
    """
    project, ada, _, _, runner = await _domain(session, tmp_path, "same-second")
    project_id = project.project_id
    frozen = datetime(2026, 9, 16, 9, 30, 0)

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr("app.service.git_operations.datetime", FrozenClock)
    service = GitService(base_path=str(tmp_path))

    first = await _submit(
        service, session, project, ada, [_upload("video-11.eaf", _revised("First"))]
    )
    second = await _submit(
        service, session, project, ada, [_upload("video-11.eaf", _revised("Second"))]
    )

    assert first["branch_name"] != second["branch_name"]
    assert {first["branch_name"], second["branch_name"]} <= _branches(runner)
    assert await _pending_count(session, project_id) == 2


@pytest.mark.asyncio
async def test_a_submitted_user_name_cannot_shape_the_branch_name(
    session: AsyncSession, tmp_path: Path
) -> None:
    """The name comes from a form field; Git refs must stay well-formed."""
    project, ada, _, _, runner = await _domain(session, tmp_path, "odd-name")

    result = await GitService(base_path=str(tmp_path)).add_elan_files(
        project.project_id,
        [_upload("video-11.eaf", _revised("Odd name"))],
        session,
        ada.user_id,
        "../main odd~name",
        protocol_validation=PROTOCOL,
    )

    assert result["branch_name"] in _branches(runner)
    assert ".." not in result["branch_name"] and " " not in result["branch_name"]


@pytest.mark.asyncio
async def test_a_colliding_submission_never_deletes_the_earlier_contribution(
    session: AsyncSession, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Should a name ever repeat, only the failing submission is cleaned up."""
    project, ada, _, _, runner = await _domain(session, tmp_path, "collision")
    project_id = project.project_id
    frozen = datetime(2026, 9, 16, 9, 30, 0)

    class FrozenClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr("app.service.git_operations.datetime", FrozenClock)
    monkeypatch.setattr("app.service.git_operations.secrets.token_hex", lambda _n: "00")
    service = GitService(base_path=str(tmp_path))
    first = await _submit(
        service, session, project, ada, [_upload("video-11.eaf", _revised("First"))]
    )

    with pytest.raises(RuntimeError):
        await _submit(
            service,
            session,
            project,
            ada,
            [_upload("video-11.eaf", _revised("Second"))],
        )

    assert first["branch_name"] in _branches(runner)
    assert await _pending_count(session, project_id) == 1
