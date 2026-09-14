from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import elan_file as elan_file_crud
from app.model.elan_file import ElanFile
from app.service import elan as elan_service_module
from app.service.elan import ElanService
from app.utils.database import DatabaseUtils


@pytest.mark.asyncio
async def test_project_lookup_uses_explicit_elan_primary_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    get_by_id = AsyncMock(return_value=SimpleNamespace(project_id=12))
    monkeypatch.setattr(DatabaseUtils, "get_by_id", get_by_id)

    result = await elan_file_crud.get_projects_for_elan_file(db, elan_id=34)

    assert result == [12]
    assert get_by_id.await_args.args[:4] == (db, ElanFile, "elan_id", 34)


@pytest.mark.asyncio
async def test_full_deletion_propagates_association_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(
        elan_file_crud,
        "get_elan_file_by_id",
        AsyncMock(return_value=SimpleNamespace(elan_id=34)),
    )
    monkeypatch.setattr(
        elan_file_crud,
        "delete_elan_file_associations",
        AsyncMock(side_effect=RuntimeError("association cleanup failed")),
    )

    with pytest.raises(RuntimeError, match="association cleanup failed"):
        await elan_file_crud.delete_elan_file_full(db, elan_id=34)

    db.delete.assert_not_awaited()


@pytest.mark.asyncio
async def test_service_does_not_report_success_when_file_deletion_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(
        elan_service_module,
        "get_project_by_name",
        AsyncMock(return_value=SimpleNamespace(project_id=12)),
    )
    monkeypatch.setattr(
        elan_service_module,
        "get_elan_file_by_filename_and_project",
        AsyncMock(return_value=SimpleNamespace(elan_id=34)),
    )
    monkeypatch.setattr(
        elan_service_module,
        "get_elan_ids_for_project",
        AsyncMock(return_value=[34]),
    )
    monkeypatch.setattr(
        elan_service_module,
        "delete_tier_groups_for_project_and_elan",
        AsyncMock(),
    )
    monkeypatch.setattr(
        elan_service_module,
        "delete_tiers_for_elan_file",
        AsyncMock(),
    )
    monkeypatch.setattr(
        elan_service_module,
        "delete_elan_file_full",
        AsyncMock(return_value=False),
    )

    deleted = await ElanService(db).delete_elan_files_from_db("sample.eaf", "project")

    assert deleted is False
    db.commit.assert_not_awaited()
    db.rollback.assert_awaited_once()
