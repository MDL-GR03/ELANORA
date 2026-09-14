from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.notification_preference import NotificationPreference
from app.service import notification as notification_service_module
from app.service.notification import NotificationService


@pytest.mark.asyncio
async def test_get_notification_preference_persists_generated_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    now = datetime.now(UTC)
    preference = NotificationPreference(
        preference_id=3,
        user_id=7,
        email_enabled=True,
        created_at=now,
        updated_at=now,
    )
    getter = AsyncMock(return_value=preference)
    monkeypatch.setattr(
        notification_service_module.notification_crud,
        "get_or_create_notification_preference",
        getter,
    )

    result = await NotificationService.get_notification_preference(db, 7)

    assert result.user_id == 7
    assert result.email_enabled is True
    db.commit.assert_awaited_once()
