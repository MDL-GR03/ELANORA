from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.instance import Instance
from app.utils.database import DatabaseUtils


async def create_instance(db: AsyncSession, data: dict[str, Any]) -> Instance:
    instance = Instance(**data)
    return await DatabaseUtils.create(db, instance)


async def get_installation_profile(db: AsyncSession) -> Instance | None:
    """Return the only institution profile configured for this installation."""
    return await db.scalar(select(Instance))


async def update_instance(
    db: AsyncSession, instance_id: int, data: dict[str, Any]
) -> Instance | None:
    await DatabaseUtils.update_by_filter(
        db, Instance, {"instance_id": instance_id}, data
    )
    return await DatabaseUtils.get_by_id(db, Instance, "instance_id", instance_id)
