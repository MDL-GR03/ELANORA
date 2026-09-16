from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError
from app.model.project_file_type import ProjectFileType
from app.service import project_naming_standard as service_module
from app.service.project_naming_standard import ProjectNamingStandardService


@pytest.mark.asyncio
async def test_import_selected_standards_is_committed_as_one_batch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    source = {
        "id": 4,
        "project_id": 1,
        "name": "Session names",
        "project_file_type_id": 7,
        "file_type_id": 3,
        "file_type_name": "ELAN",
        "pattern": "{session}",
        "description": None,
        "components": [],
    }
    source_pft = ProjectFileType(id=7, project_id=1, file_type_id=3, name="ELAN")
    target_pft = ProjectFileType(id=8, project_id=2, file_type_id=3, name="ELAN")
    db.get.return_value = source_pft
    monkeypatch.setattr(
        ProjectNamingStandardService,
        "get_standard_with_components",
        AsyncMock(return_value=source),
    )
    monkeypatch.setattr(
        service_module,
        "get_project_file_type_by_project_and_file_type",
        AsyncMock(return_value=target_pft),
    )
    creator = AsyncMock(
        return_value={**source, "project_id": 2, "project_file_type_id": 8}
    )
    monkeypatch.setattr(
        ProjectNamingStandardService, "create_standard_with_components", creator
    )

    result = await ProjectNamingStandardService.import_selected_standards(db, 2, [4])

    assert len(result.imported_standards) == 1
    assert creator.await_args.kwargs["commit"] is False
    db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_import_missing_standard_rolls_back_instead_of_silently_skipping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    monkeypatch.setattr(
        ProjectNamingStandardService,
        "get_standard_with_components",
        AsyncMock(return_value=None),
    )

    with pytest.raises(ElanoraError) as caught:
        await ProjectNamingStandardService.import_selected_standards(db, 2, [404])

    assert caught.value.status_code == 404
    db.rollback.assert_awaited_once()
    db.commit.assert_not_awaited()
