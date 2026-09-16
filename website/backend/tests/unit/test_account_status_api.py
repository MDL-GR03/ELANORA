"""The account lifecycle endpoint publishes fixed, non-revealing refusals."""

from unittest.mock import AsyncMock, Mock

import pytest

import app.api.v1.user as user_api
from app.core.errors import ElanoraError, ErrorCode
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
        (AccountNotFoundError, 404, ErrorCode.ACCOUNT_NOT_FOUND),
        (AdministratorNoLongerActiveError, 403, ErrorCode.ADMINISTRATOR_INACTIVE),
        (SelfAccountStatusError, 409, ErrorCode.SELF_STATUS_CHANGE_REFUSED),
        (LastAdministratorError, 409, ErrorCode.LAST_ADMINISTRATOR_REFUSED),
        (RedundantAccountStatusError, 409, ErrorCode.ACCOUNT_STATUS_UNCHANGED),
    ],
)
@pytest.mark.asyncio
async def test_status_refusals_never_publish_exception_text(
    monkeypatch: pytest.MonkeyPatch,
    raised: type[Exception],
    expected_status: int,
    expected_detail: ErrorCode,
) -> None:
    monkeypatch.setattr(
        user_account_status,
        "set_account_active",
        AsyncMock(side_effect=raised(SENSITIVE_VALUE)),
    )

    with pytest.raises(ElanoraError) as error:
        await user_api.set_institution_account_status(
            7,
            AccountStatusRequest(is_active=False, reason="Offboarding"),
            Mock(),
            Mock(),
        )

    assert error.value.status_code == expected_status
    assert error.value.code == expected_detail
    assert SENSITIVE_VALUE not in error.value.message


def test_a_reason_is_required_for_every_status_change() -> None:
    with pytest.raises(ValueError, match="at least 3 characters"):
        AccountStatusRequest(is_active=False, reason="no")
