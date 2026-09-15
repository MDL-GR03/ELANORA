"""Protocol administration over HTTP, as the project configuration page uses it."""

from pathlib import Path

import pytest
from conftest import GIT, PROJECT, Browser, InstitutionAccounts, project_with_member
from httpx import AsyncClient

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


async def _accepted_corpus(browser: Browser, accounts: InstitutionAccounts) -> int:
    project_id = await project_with_member(browser, accounts)
    uploaded = await browser.upload(project_id, "session-001.eaf", FIXTURE.read_bytes())
    assert uploaded.status_code == 200, uploaded.text
    pending = await browser.get(f"{GIT}/projects/{PROJECT}/admin/pending-uploads")
    (contribution,) = pending.json()["pending_uploads"]
    accepted = await browser.post(
        f"{GIT}/projects/{PROJECT}/admin/pending-uploads/"
        f"{contribution['branch_name']}/merge",
        json={"resolution_strategy": "auto"},
    )
    assert accepted.status_code == 200, accepted.text
    return project_id


@pytest.mark.asyncio
async def test_a_protocol_version_is_edited_published_scanned_and_withdrawn(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await _accepted_corpus(browser, institution_accounts)
    base = f"/api/v1/projects/{project_id}"

    suggestion = await browser.get(f"{base}/protocol-suggestions")
    assert suggestion.status_code == 200, suggestion.text
    assert "utterance" in suggestion.json()["proposed_rules"]["required_tiers"]

    created = await browser.post(
        f"{base}/protocols",
        json={"name": "Corpus rules", "rules": {"required_tiers": ["utterance"]}},
    )
    assert created.status_code == 201, created.text
    protocol_id = created.json()["protocol_id"]
    draft_id = created.json()["versions"][0]["protocol_version_id"]

    edited = await browser.put(
        f"{base}/protocol-versions/{draft_id}",
        json={"rules": {"required_tiers": ["utterance", "gloss"]}},
    )
    assert edited.status_code == 200, edited.text
    assert edited.json()["rules"]["required_tiers"] == ["gloss", "utterance"]

    spare = await browser.post(
        f"{base}/protocols/{protocol_id}/versions",
        json={"rules": {"required_tiers": ["utterance"]}},
    )
    assert spare.status_code == 201, spare.text
    deleted = await browser.client.delete(
        f"{base}/protocol-versions/{spare.json()['protocol_version_id']}",
        headers={"X-CSRF-Token": browser.csrf},
    )
    assert deleted.status_code == 204, deleted.text

    published = await browser.post(f"{base}/protocol-versions/{draft_id}/publish")
    assert published.status_code == 200, published.text
    assert published.json()["rules_sha256"]
    immutable = await browser.put(
        f"{base}/protocol-versions/{draft_id}",
        json={"rules": {"required_tiers": []}},
    )
    assert immutable.status_code == 409

    scan = await browser.post(
        f"{base}/protocol-versions/{draft_id}/compliance-scans?preview=true"
    )
    assert scan.status_code == 201, scan.text
    assert scan.json()["failed_files"] == 1, "the fixture has no gloss tier"
    scans = await browser.get(f"{base}/compliance-scans")
    assert scans.status_code == 200, scans.text
    assert len(scans.json()) == 1

    archived = await browser.post(
        f"{base}/protocol-versions/{draft_id}/archive",
        json={"reason": "Published by mistake"},
    )
    assert archived.status_code == 200, archived.text
    assert archived.json()["archived_at"] is not None
    pin_archived = await browser.put(f"{base}/protocol-version/{draft_id}")
    assert pin_archived.status_code == 409

    purged = await browser.client.delete(
        f"{base}/protocol-versions/{draft_id}/purge",
        headers={"X-CSRF-Token": browser.csrf},
    )
    assert purged.status_code == 204, purged.text
    listed = await browser.get(f"{base}/protocols")
    assert listed.status_code == 200, listed.text
    remaining = [
        version["protocol_version_id"]
        for protocol in listed.json()
        for version in protocol["versions"]
    ]
    assert draft_id not in remaining


@pytest.mark.asyncio
async def test_protocol_management_can_be_delegated_and_withdrawn(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)
    base = f"/api/v1/projects/{project_id}"
    rules = {"rules": {"required_tiers": ["utterance"]}}

    await browser.sign_in(institution_accounts.researcher_login)
    before = await browser.post(f"{base}/protocols", json={"name": "Before", **rules})
    assert before.status_code == 403

    await browser.sign_in(institution_accounts.admin_login)
    granted = await browser.put(
        f"{base}/protocol-managers/{institution_accounts.researcher_id}"
    )
    assert granted.status_code == 200, granted.text

    await browser.sign_in(institution_accounts.researcher_login)
    during = await browser.post(f"{base}/protocols", json={"name": "During", **rules})
    assert during.status_code == 201, during.text

    await browser.sign_in(institution_accounts.admin_login)
    revoked = await browser.client.delete(
        f"{base}/protocol-managers/{institution_accounts.researcher_id}",
        headers={"X-CSRF-Token": browser.csrf},
    )
    assert revoked.status_code == 204, revoked.text

    await browser.sign_in(institution_accounts.researcher_login)
    after = await browser.post(f"{base}/protocols", json={"name": "After", **rules})
    assert after.status_code == 403
