from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.association import (
    add_project_annot_standard,
    delete_project_associations,
)
from app.model.association import ProjectAnnotStandard
from app.utils.database import DatabaseUtils


@pytest.mark.asyncio
async def test_annotation_standard_association_uses_model_column(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    get_existing = AsyncMock(return_value=None)
    create = AsyncMock()
    monkeypatch.setattr(DatabaseUtils, "get_one_by_filter", get_existing)
    monkeypatch.setattr(DatabaseUtils, "create", create)

    await add_project_annot_standard(db, project_id=7, standard_id="schema-v1")

    assert get_existing.await_args.args[2] == {
        "project_id": 7,
        "standard_id": "schema-v1",
    }
    association = create.await_args.args[1]
    assert isinstance(association, ProjectAnnotStandard)
    assert association.project_id == 7
    assert association.standard_id == "schema-v1"


@pytest.mark.asyncio
async def test_project_association_deletion_propagates_database_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db = AsyncMock(spec=AsyncSession)
    failure = RuntimeError("database unavailable")
    monkeypatch.setattr(DatabaseUtils, "bulk_delete", AsyncMock(side_effect=failure))

    with pytest.raises(RuntimeError, match="database unavailable"):
        await delete_project_associations(db, project_id=7)

    db.rollback.assert_awaited_once()
