"""Requesting changes, answering them and declining, over HTTP."""

from pathlib import Path

import pytest
from conftest import GIT, PROJECT, Browser, InstitutionAccounts, project_with_member
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
PENDING = f"{GIT}/projects/{PROJECT}/admin/pending-uploads"


def _revised(label: str) -> bytes:
    content = FIXTURE.read_bytes()
    revised = content.replace(b">Hello<", f">{label}<".encode(), 1)
    assert revised != content
    return revised


async def _pending(browser: Browser) -> list[dict]:
    response = await browser.get(PENDING)
    assert response.status_code == 200, response.text
    return response.json()["pending_uploads"]


@pytest.mark.asyncio
async def test_requested_changes_are_answered_and_the_correction_accepted(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)
    cases = f"/api/v1/review/projects/{project_id}/cases"

    await browser.sign_in(institution_accounts.researcher_login)
    first = await browser.upload(project_id, "session-001.eaf", _revised("Helo"))
    assert first.status_code == 200, first.text

    await browser.sign_in(institution_accounts.admin_login)
    (original,) = await _pending(browser)
    opened = await browser.post(
        cases,
        json={
            "upload_id": original["upload_id"],
            "request_changes": True,
            "title": "Fix the greeting",
            "filename": "session-001.eaf",
            "initial_comment": "The first annotation is misspelled.",
        },
    )
    assert opened.status_code == 201, opened.text
    case = opened.json()
    assert case["state"] == "changes_requested"
    blocked = await browser.post(
        f"{PENDING}/{original['branch_name']}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert blocked.status_code == 409, "open requested changes block acceptance"

    await browser.sign_in(institution_accounts.researcher_login)
    corrected = await browser.upload(
        project_id,
        "session-001.eaf",
        _revised("Hello there"),
        correction_case_id=case["case_id"],
    )
    assert corrected.status_code == 200, corrected.text
    correction = next(
        item
        for item in await _pending(browser)
        if item["upload_id"] != original["upload_id"]
    )
    linked = await browser.post(
        f"{cases}/{case['case_id']}/resubmission",
        json={"upload_id": correction["upload_id"]},
    )
    assert linked.status_code == 200, linked.text
    assert linked.json()["state"] == "resubmitted"
    self_resolved = await browser.client.patch(
        f"{cases}/{case['case_id']}",
        headers={"X-CSRF-Token": browser.csrf},
        json={"state": "resolved"},
    )
    assert self_resolved.status_code == 403, "researchers cannot close their case"

    await browser.sign_in(institution_accounts.admin_login)
    resolved = await browser.client.patch(
        f"{cases}/{case['case_id']}",
        headers={"X-CSRF-Token": browser.csrf},
        json={"state": "resolved"},
    )
    assert resolved.status_code == 200, resolved.text
    accepted = await browser.post(
        f"{PENDING}/{correction['branch_name']}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert accepted.status_code == 200, accepted.text

    raw = await session.scalar(
        select(EafRevision.raw_xml)
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project_id)
        .order_by(EafRevision.revision_number.desc())
        .limit(1)
    )
    assert raw is not None and b">Hello there<" in raw


@pytest.mark.asyncio
async def test_a_declined_contribution_leaves_the_queue_with_its_reason(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)
    await browser.sign_in(institution_accounts.researcher_login)
    await browser.upload(project_id, "session-001.eaf", FIXTURE.read_bytes())
    (contribution,) = await _pending(browser)

    refused = await browser.post(
        f"{PENDING}/{contribution['upload_id']}/decline",
        json={"reason": "Not part of this corpus"},
    )
    assert refused.status_code == 403

    await browser.sign_in(institution_accounts.admin_login)
    declined = await browser.post(
        f"{PENDING}/{contribution['upload_id']}/decline",
        json={"reason": "Not part of this corpus"},
    )
    assert declined.status_code == 200, declined.text
    remaining = await browser.get(PENDING)
    assert remaining.json()["total_pending"] == 0
    files = await browser.get(f"{GIT}/projects/{PROJECT}/files")
    assert "session-001.eaf" not in files.text
