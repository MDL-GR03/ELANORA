from unittest.mock import AsyncMock

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.file_type import FileType
from app.service import file_type as file_type_service_module
from app.service.file_type import FileTypeService


@pytest.mark.asyncio
async def test_global_file_type_creation_stores_only_extension(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    file_type = FileType(extension=".eaf")
    creator = AsyncMock(return_value=file_type)
    monkeypatch.setattr(
        file_type_service_module.file_type_crud, "create_file_type", creator
    )

    result = await FileTypeService.create_file_type(db, "ELAN", ".eaf")

    assert result is file_type
    creator.assert_awaited_once_with(db, ".eaf")
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_unknown_file_type_integrity_error_is_not_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    error = IntegrityError("delete", {}, Exception("unexpected constraint"))
    monkeypatch.setattr(
        file_type_service_module.file_type_crud,
        "delete_file_type",
        AsyncMock(side_effect=error),
    )

    with pytest.raises(IntegrityError):
        await FileTypeService.delete_file_type(db, 7)

    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
