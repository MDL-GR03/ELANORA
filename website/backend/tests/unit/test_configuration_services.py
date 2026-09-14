from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.effective_naming_standard import EffectiveNamingStandard
from app.model.project_location_file_type import ProjectLocationFileType
from app.service import effective_naming_standard, project_location_file_type


@pytest.mark.asyncio
async def test_assign_effective_standard_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    standard = EffectiveNamingStandard(
        project_id=1,
        project_file_type_id=2,
        naming_standard_id=3,
        location_id=4,
    )
    setter = AsyncMock(return_value=standard)
    monkeypatch.setattr(effective_naming_standard, "set_effective_standard", setter)

    result = await effective_naming_standard.assign_effective_standard(db, 1, 2, 3, 4)

    assert result is standard
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_assign_effective_standard_rolls_back_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    setter = AsyncMock(side_effect=RuntimeError("assignment failed"))
    monkeypatch.setattr(effective_naming_standard, "set_effective_standard", setter)

    with pytest.raises(RuntimeError, match="assignment failed"):
        await effective_naming_standard.assign_effective_standard(db, 1, 2, 3, 4)

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_add_location_file_type_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    association = ProjectLocationFileType(
        project_id=1,
        location_id=2,
        project_file_type_id=3,
    )
    creator = AsyncMock(return_value=association)
    monkeypatch.setattr(
        project_location_file_type, "add_file_type_to_location", creator
    )

    result = await project_location_file_type.service_add_file_type_to_location(
        db, 1, 2, 3
    )

    assert result is association
    db.commit.assert_awaited_once()
    db.rollback.assert_not_awaited()


@pytest.mark.asyncio
async def test_remove_location_file_type_rolls_back_and_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    remover = AsyncMock(side_effect=RuntimeError("removal failed"))
    monkeypatch.setattr(
        project_location_file_type, "remove_file_type_from_location", remover
    )

    with pytest.raises(RuntimeError, match="removal failed"):
        await project_location_file_type.service_remove_file_type_from_location(
            db, 1, 2, 3
        )

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
