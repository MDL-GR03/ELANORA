from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

import app.utils.database as database_module
from app.model.accepted_value import AcceptedValue
from app.utils.database import DatabaseUtils


@pytest.mark.asyncio
async def test_bulk_insert_chunks_statements_below_driver_limit(monkeypatch) -> None:
    monkeypatch.setattr(database_module, "MAX_BULK_BIND_PARAMETERS", 2)
    session = SimpleNamespace(
        bind=SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        execute=AsyncMock(),
    )

    await DatabaseUtils.bulk_insert(
        session,
        AcceptedValue,
        [{"value": f"value-{index}"} for index in range(5)],
    )

    assert session.execute.await_count == 3


@pytest.mark.asyncio
async def test_delete_by_id_deletes_existing_instance(monkeypatch) -> None:
    instance = AcceptedValue(value="example")
    session = SimpleNamespace(delete=AsyncMock())
    lookup = AsyncMock(return_value=instance)
    monkeypatch.setattr(DatabaseUtils, "get_by_id", lookup)

    deleted = await DatabaseUtils.delete_by_id(session, AcceptedValue, "id", 17)

    assert deleted is True
    lookup.assert_awaited_once_with(session, AcceptedValue, "id", 17)
    session.delete.assert_awaited_once_with(instance)


@pytest.mark.asyncio
async def test_delete_by_id_reports_missing_instance(monkeypatch) -> None:
    session = SimpleNamespace(delete=AsyncMock())
    monkeypatch.setattr(DatabaseUtils, "get_by_id", AsyncMock(return_value=None))

    deleted = await DatabaseUtils.delete_by_id(session, AcceptedValue, "id", 17)

    assert deleted is False
    session.delete.assert_not_awaited()
