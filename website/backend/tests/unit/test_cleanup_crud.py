from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.annotation import delete_annotations_by_file
from app.crud.invitation import delete_project_invitations
from app.crud.tier import delete_tiers_for_elan_file
from app.utils.database import DatabaseUtils


@pytest.mark.asyncio
async def test_annotation_cleanup_propagates_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(
        DatabaseUtils,
        "bulk_delete",
        AsyncMock(side_effect=RuntimeError("annotation cleanup failed")),
    )

    with pytest.raises(RuntimeError, match="annotation cleanup failed"):
        await delete_annotations_by_file(db, elan_id=4)


@pytest.mark.asyncio
async def test_tier_cleanup_propagates_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    tier_ids = SimpleNamespace(scalars=lambda: SimpleNamespace(all=lambda: [8]))
    db = AsyncMock(spec=AsyncSession)
    db.execute.return_value = tier_ids
    monkeypatch.setattr(
        DatabaseUtils,
        "bulk_delete",
        AsyncMock(side_effect=RuntimeError("tier cleanup failed")),
    )

    with pytest.raises(RuntimeError, match="tier cleanup failed"):
        await delete_tiers_for_elan_file(db, elan_id=4)


@pytest.mark.asyncio
async def test_invitation_cleanup_propagates_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(
        DatabaseUtils,
        "bulk_delete",
        AsyncMock(side_effect=RuntimeError("invitation cleanup failed")),
    )

    with pytest.raises(RuntimeError, match="invitation cleanup failed"):
        await delete_project_invitations(db, project_id=2)
