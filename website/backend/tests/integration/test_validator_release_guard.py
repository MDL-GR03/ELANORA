"""The validator release guard, against real PostgreSQL rows."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.protocol import ValidatorRelease
from app.service.protocol import ProtocolConflictError, _validator_release
from app.service.protocol_evaluation import (
    VALIDATOR_NAME,
    VALIDATOR_VERSION,
    validator_checksum,
)


@pytest.mark.asyncio
async def test_the_first_validation_records_the_current_release(
    session: AsyncSession,
) -> None:
    release = await _validator_release(session)

    assert release.name == VALIDATOR_NAME
    assert release.version == VALIDATOR_VERSION
    assert release.checksum_sha256 == validator_checksum()
    assert await _validator_release(session) is release


@pytest.mark.asyncio
async def test_changed_validation_sources_under_the_same_version_stop_validation(
    session: AsyncSession,
) -> None:
    """Silently reusing a version would change what recorded runs mean."""
    session.add(
        ValidatorRelease(
            name=VALIDATOR_NAME,
            version=VALIDATOR_VERSION,
            checksum_sha256="0" * 64,
        )
    )
    await session.flush()

    with pytest.raises(ProtocolConflictError, match="without a validator version"):
        await _validator_release(session)


@pytest.mark.asyncio
async def test_a_new_version_gets_its_own_release_and_keeps_the_old_one(
    session: AsyncSession,
) -> None:
    previous = ValidatorRelease(
        name=VALIDATOR_NAME, version="1", checksum_sha256="1" * 64
    )
    session.add(previous)
    await session.flush()

    current = await _validator_release(session)

    assert current.version == VALIDATOR_VERSION != previous.version
    releases = await session.scalar(select(func.count()).select_from(ValidatorRelease))
    assert releases == 2
    assert previous.checksum_sha256 == "1" * 64
