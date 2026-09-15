"""Per-project data classification, legal basis, retention and legal hold."""

import pytest
from conftest import Browser, InstitutionAccounts, project_with_member
from httpx import AsyncClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent

SENSITIVE = {
    "data_classification": "sensitive_personal",
    "legal_basis": "Consent forms LSFB-2026, ethics approval EC-114",
    "retention_days": 3650,
    "legal_hold": False,
    "legal_hold_reason": None,
}


def _url(project_id: int) -> str:
    return f"/api/v1/projects/{project_id}/data-governance"


@pytest.mark.asyncio
async def test_a_new_project_starts_unclassified_and_kept_indefinitely(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)

    response = await browser.get(_url(project_id))

    assert response.status_code == 200, response.text
    assert response.json() == {
        "data_classification": None,
        "legal_basis": None,
        "retention_days": None,
        "legal_hold": False,
        "legal_hold_reason": None,
        "updated_at": None,
        "updated_by": None,
    }


@pytest.mark.asyncio
async def test_administrators_record_governance_and_every_change_is_audited(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)

    saved = await browser.put(_url(project_id), json=SENSITIVE)
    assert saved.status_code == 200, saved.text
    held = await browser.put(
        _url(project_id),
        json={**SENSITIVE, "legal_hold": True, "legal_hold_reason": "Audit 2026-17"},
    )
    assert held.status_code == 200, held.text

    body = held.json()
    assert body["data_classification"] == "sensitive_personal"
    assert body["legal_hold"] is True
    assert body["updated_by"] == institution_accounts.admin_id
    assert body["updated_at"] is not None
    events = (
        await session.scalars(
            select(AuditEvent)
            .where(AuditEvent.action == "project.data_governance.updated")
            .order_by(AuditEvent.occurred_at)
        )
    ).all()
    assert len(events) == 2
    assert events[0].details["before"]["data_classification"] is None
    assert events[1].details["before"]["legal_hold"] is False
    assert events[1].details["after"]["legal_hold_reason"] == "Audit 2026-17"


@pytest.mark.asyncio
async def test_members_can_read_but_only_administrators_change_governance(
    api_client: AsyncClient, institution_accounts: InstitutionAccounts
) -> None:
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)
    await browser.put(_url(project_id), json=SENSITIVE)

    await browser.sign_in(institution_accounts.researcher_login)
    readable = await browser.get(_url(project_id))
    refused = await browser.put(
        _url(project_id), json={**SENSITIVE, "data_classification": "public"}
    )
    await browser.sign_in(institution_accounts.outsider_login)
    outsider = await browser.get(_url(project_id))

    assert readable.status_code == 200
    assert readable.json()["data_classification"] == "sensitive_personal"
    assert refused.status_code == 403
    assert outsider.status_code in {403, 404}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "change",
    [
        {"legal_basis": None},
        {"legal_basis": "   "},
        {"legal_hold": True, "legal_hold_reason": None},
        {"retention_days": 7},
        {"data_classification": "secret"},
    ],
)
async def test_incomplete_governance_is_refused(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    change: dict[str, object],
) -> None:
    """Personal data needs a legal basis; a hold needs a reason."""
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)

    response = await browser.put(_url(project_id), json={**SENSITIVE, **change})

    # The application reports request validation failures as 400.
    assert response.status_code == 400, response.text
    assert (await browser.get(_url(project_id))).json()["data_classification"] is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("column_values", "constraint"),
    [
        (
            {"data_classification": "sensitive_personal", "legal_basis": " "},
            "ck_project_sensitive_legal_basis",
        ),
        ({"legal_hold": True}, "ck_project_legal_hold_reason"),
        ({"retention_days": 1}, "ck_project_retention_days"),
    ],
)
async def test_the_database_refuses_incomplete_governance_from_any_writer(
    api_client: AsyncClient,
    institution_accounts: InstitutionAccounts,
    session: AsyncSession,
    column_values: dict[str, object],
    constraint: str,
) -> None:
    """Workers and scripts cannot skip the rules the API enforces."""
    browser = Browser(api_client)
    project_id = await project_with_member(browser, institution_accounts)
    assignments = ", ".join(f"{column} = :{column}" for column in column_values)

    with pytest.raises(IntegrityError, match=constraint):
        await session.execute(
            text(f'UPDATE "PROJECT" SET {assignments} WHERE project_id = :id'),  # noqa: S608
            {**column_values, "id": project_id},
        )
    await session.rollback()
