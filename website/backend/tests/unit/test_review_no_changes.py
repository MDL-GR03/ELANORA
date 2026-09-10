import uuid
from unittest.mock import AsyncMock, Mock

import pytest

from app.model.enums import ReviewCaseState, Severity, Status, Type
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.review import ReviewCase
from app.service import review as review_service


@pytest.mark.asyncio
async def test_approved_matching_correction_is_a_successful_no_change_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project = Project(project_id=7, project_name="Corpus", project_path="/corpus")
    original = PendingUpload(
        upload_id=11,
        upload_type=Type.PENDING_UPLOAD,
        upload_description="Original",
        severity=Severity.LOW,
        status=Status.PENDING_ADMIN_APPROVAL,
        project_id=7,
        submitted_by=4,
    )
    corrected = PendingUpload(
        upload_id=12,
        upload_type=Type.PENDING_UPLOAD,
        upload_description="Corrected",
        severity=Severity.LOW,
        status=Status.PENDING_ADMIN_APPROVAL,
        project_id=7,
        branch_name="correction-12",
    )
    case = ReviewCase(
        case_id=uuid.uuid4(),
        project_id=7,
        upload_id=11,
        resubmitted_upload_id=12,
        title="Restore annotation",
        state=ReviewCaseState.RESUBMITTED.value,
    )
    case.upload = original
    case.resubmission = corrected

    runner = Mock()
    runner.get_tree_hash.side_effect = lambda revision="HEAD": "same-tree"
    monkeypatch.setattr(review_service, "GitCommandRunner", Mock(return_value=runner))
    db = Mock()
    db.get = AsyncMock(return_value=project)

    await review_service._resolve_approved_correction(db, case, actor_id=2)

    assert case.state == ReviewCaseState.RESOLVED.value
    assert corrected.status == Status.NO_CHANGES
    assert corrected.resolved_by == 2
    assert corrected.resolved_at is not None
    assert any(
        getattr(call.args[0], "action", None) == "contribution.no_project_changes"
        for call in db.add.call_args_list
    )
