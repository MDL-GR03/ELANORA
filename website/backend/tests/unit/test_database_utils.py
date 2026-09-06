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
