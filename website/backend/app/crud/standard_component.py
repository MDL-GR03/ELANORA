from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.component_template import ComponentTemplate
from app.model.standard_component import StandardComponent
from app.utils.database import DatabaseUtils


async def link_standard_to_component(
    db: AsyncSession, naming_standard_id: int, component_template_id: int, order: int
) -> StandardComponent:
    filters = {
        "naming_standard_id": naming_standard_id,
        "component_template_id": component_template_id,
    }
    link = await DatabaseUtils.get_one_by_filter(db, StandardComponent, filters)
    if not link:
        link = StandardComponent(
            naming_standard_id=naming_standard_id,
            component_template_id=component_template_id,
            order=order,
        )
        await DatabaseUtils.create(db, link)
        await db.flush()
    return link


async def unlink_standard_from_component(
    db: AsyncSession, naming_standard_id: int, component_template_id: int
) -> int:
    return await DatabaseUtils.delete_by_filter(
        db,
        StandardComponent,
        naming_standard_id=naming_standard_id,
        component_template_id=component_template_id,
    )


async def get_components_by_standard(
    db: AsyncSession, naming_standard_id: int
) -> list[StandardComponent]:
    return await DatabaseUtils.get_by_filter(
        db,
        StandardComponent,
        filters={"naming_standard_id": naming_standard_id},
        order_by=[StandardComponent.order],
        options=[
            selectinload(StandardComponent.component_template).selectinload(
                ComponentTemplate.accepted_values
            )
        ],
    )


async def get_by_standard(
    db: AsyncSession, standard_id: int
) -> list[StandardComponent]:
    return await DatabaseUtils.get_by_filter(
        db, StandardComponent, {"naming_standard_id": standard_id}
    )
