"""A contribution's whole life over HTTP, through the real application.

An administrator creates a project and adds a researcher; the researcher
uploads; the administrator reviews and accepts; the accepted revision is then
validated against a pinned protocol. Each step uses the endpoints, cookies,
CSRF checks and permission guards a browser meets.
"""

from pathlib import Path

import pytest
from conftest import ACCOUNT_PASSWORD, InstitutionAccounts
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
GIT = "/api/v1/git"
PROJECT = "http-corpus"


class Browser:
    """One signed-in browser tab: cookies plus the CSRF header it echoes."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.csrf = ""

    async def sign_in(self, login: str) -> None:
        self.client.cookies.clear()
        response = await self.client.post(
            "/api/v1/auth/login", json={"login": login, "password": ACCOUNT_PASSWORD}
        )
        assert response.status_code == 200, response.text
        self.csrf = response.json()["csrf_token"]

    async def get(self, url: str):
        return await self.client.get(url)

    async def post(self, url: str, **kwargs):
        return await self.client.post(
            url, headers={"X-CSRF-Token": self.csrf}, **kwargs
        )

    async def put(self, url: str, **kwargs):
        return await self.client.put(url, headers={"X-CSRF-Token": self.csrf}, **kwargs)

    async def upload(self, project_id: int, filename: str, content: bytes):
        return await self.post(
            f"{GIT}/projects/{project_id}/upload",
            data={
                "user_name": "researcher",
                "contribution_summary": "Session one annotations",
            },
            files=[("files", (filename, content, "application/xml"))],
        )


async def _project_with_member(browser: Browser, accounts: InstitutionAccounts) -> int:
    await browser.sign_in(accounts.admin_login)
    created = await browser.post(
        f"{GIT}/projects/create",
        json={"project_name": PROJECT, "description": "HTTP workflow"},
    )
    assert created.status_code == 200, created.text
    listed = await browser.get(f"{GIT}/projects")
    (project,) = listed.json()["projects"]
    added = await browser.post(
        f"/api/v1/project-associations/projects/{project['project_id']}/users",
        json={"user_id": accounts.researcher_id, "permission": "write"},
    )
    assert added.status_code == 200, added.text
    return project["project_id"]


@pytest.mark.asyncio
async def test_a_contribution_goes_from_upload_to_accepted_and_validated(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    browser = Browser(api_client)
    project_id = await _project_with_member(browser, institution_accounts)

    await browser.sign_in(institution_accounts.researcher_login)
    uploaded = await browser.upload(project_id, "session-001.eaf", FIXTURE.read_bytes())
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["status"] == "pending_admin_approval"

    pending = await browser.get(f"{GIT}/projects/{PROJECT}/admin/pending-uploads")
    assert pending.status_code == 200, pending.text
    (contribution,) = pending.json()["pending_uploads"]
    branch = contribution["branch_name"]
    refused = await browser.post(
        f"{GIT}/projects/{PROJECT}/admin/pending-uploads/{branch}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert refused.status_code == 403, "a researcher cannot accept their own work"

    await browser.sign_in(institution_accounts.admin_login)
    accepted = await browser.post(
        f"{GIT}/projects/{PROJECT}/admin/pending-uploads/{branch}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert accepted.status_code == 200, accepted.text
    remaining = await browser.get(f"{GIT}/projects/{PROJECT}/admin/pending-uploads")
    assert remaining.json()["total_pending"] == 0
    files = await browser.get(f"{GIT}/projects/{PROJECT}/files")
    assert files.status_code == 200, files.text
    assert "session-001.eaf" in files.text

    protocol = await browser.post(
        f"/api/v1/projects/{project_id}/protocols",
        json={
            "name": "HTTP protocol",
            "rules": {
                "required_tiers": ["utterance", "gloss"],
                "severities": {"required_tiers": "warning"},
            },
        },
    )
    assert protocol.status_code == 201, protocol.text
    version_id = protocol.json()["versions"][0]["protocol_version_id"]
    published = await browser.post(
        f"/api/v1/projects/{project_id}/protocol-versions/{version_id}/publish"
    )
    assert published.status_code == 200, published.text
    next_draft = await browser.post(
        f"/api/v1/projects/{project_id}/protocols/"
        f"{protocol.json()['protocol_id']}/versions",
        json={"rules": {"required_tiers": ["utterance"]}},
    )
    assert next_draft.status_code == 201, next_draft.text
    pinned = await browser.put(
        f"/api/v1/projects/{project_id}/protocol-version/{version_id}"
    )
    assert pinned.status_code == 200, pinned.text

    revision_id = await session.scalar(
        select(EafRevision.revision_id)
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(
            ElanFile.project_id == project_id,
            ElanFile.filename == "session-001.eaf",
        )
    )
    assert revision_id is not None, "acceptance must record an EAF revision"
    run = await browser.post(
        f"/api/v1/projects/{project_id}/revisions/{revision_id}/validations"
    )
    assert run.status_code == 200, run.text
    assert run.json()["outcome"] == "passed"
    assert [issue["code"] for issue in run.json()["issues"]] == [
        "protocol.required_tier_missing"
    ]


@pytest.mark.asyncio
async def test_an_invalid_eaf_is_refused_with_its_findings(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await _project_with_member(browser, institution_accounts)
    await browser.sign_in(institution_accounts.researcher_login)
    broken = FIXTURE.read_bytes().replace(
        b'ANNOTATION_REF="a1"', b'ANNOTATION_REF="missing"', 1
    )

    response = await browser.upload(project_id, "session-002.eaf", broken)

    assert response.status_code == 422, response.text
    detail = response.json()["detail"]
    assert detail["code"] == "invalid_eaf_batch"
    (rejected,) = detail["rejected_files"]
    assert rejected["filename"] == "session-002.eaf"
    assert "unknown_annotation_ref" in {issue["code"] for issue in rejected["issues"]}


@pytest.mark.asyncio
async def test_people_outside_the_project_cannot_upload(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await _project_with_member(browser, institution_accounts)

    await browser.sign_in(institution_accounts.outsider_login)
    outsider = await browser.upload(project_id, "session-003.eaf", FIXTURE.read_bytes())
    # A visitor with no session, but a well-formed CSRF pair.
    browser.client.cookies.clear()
    api_client.cookies.set("elanora_csrf", "t", domain="localhost.local")
    anonymous = await api_client.post(
        f"{GIT}/projects/{project_id}/upload",
        headers={"X-CSRF-Token": "t"},
        data={"user_name": "x", "contribution_summary": "nothing"},
        files=[("files", ("session-003.eaf", FIXTURE.read_bytes(), "application/xml"))],
    )

    assert outsider.status_code in {403, 404}, outsider.text
    assert anonymous.status_code == 401, anonymous.text
