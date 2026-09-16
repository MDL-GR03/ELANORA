"""The account lifecycle endpoint publishes fixed, non-revealing refusals."""

from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException

import app.api.v1.user as user_api
from app.schema.requests.user import AccountStatusRequest
from app.service import user_account_status
from app.service.user_errors import (
    AccountNotFoundError,
    AdministratorNoLongerActiveError,
    LastAdministratorError,
    RedundantAccountStatusError,
    SelfAccountStatusError,
)

SENSITIVE_VALUE = "curator@example.org row 4711 internal-detail"


@pytest.mark.parametrize(
    ("raised", "expected_status", "expected_detail"),
    [
        (AccountNotFoundError, 404, user_api.ACCOUNT_NOT_FOUND),
        (
            AdministratorNoLongerActiveError,
            403,
            user_api.ADMINISTRATOR_NO_LONGER_ACTIVE,
        ),
        (SelfAccountStatusError, 409, user_api.SELF_STATUS_CHANGE_REFUSED),
        (LastAdministratorError, 409, user_api.LAST_ADMINISTRATOR_REFUSED),
        (RedundantAccountStatusError, 409, user_api.REDUNDANT_ACCOUNT_STATUS),
    ],
)
@pytest.mark.asyncio
async def test_status_refusals_never_publish_exception_text(
    monkeypatch: pytest.MonkeyPatch,
    raised: type[Exception],
    expected_status: int,
    expected_detail: str,
) -> None:
    monkeypatch.setattr(
        user_account_status,
        "set_account_active",
        AsyncMock(side_effect=raised(SENSITIVE_VALUE)),
    )

    with pytest.raises(HTTPException) as error:
        await user_api.set_institution_account_status(
            7,
            AccountStatusRequest(is_active=False, reason="Offboarding"),
            Mock(),
            Mock(),
        )

    assert error.value.status_code == expected_status
    assert error.value.detail == expected_detail
    assert SENSITIVE_VALUE not in str(error.value.detail)


def test_a_reason_is_required_for_every_status_change() -> None:
    with pytest.raises(ValueError, match="at least 3 characters"):
        AccountStatusRequest(is_active=False, reason="no")
