from typing import cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.component_template import ComponentTemplate
from app.model.project_file_type import ProjectFileType
from app.model.standard_component import StandardComponent
from app.utils.database import DatabaseUtils


async def get_or_create_component_template(
    db: AsyncSession, file_type_id: int, name: str, regex: str, description: str | None
) -> ComponentTemplate:
    filters = {
        "file_type_id": file_type_id,
        "name": name,
        "regex": regex,
        "description": description,
    }
    template = await DatabaseUtils.get_one_by_filter(db, ComponentTemplate, filters)
    if template:
        return template
    template = ComponentTemplate(
        file_type_id=file_type_id, name=name, regex=regex, description=description
    )
    await DatabaseUtils.create(db, template)
    await db.flush()
    return template


async def get_component_templates_by_file_type(
    db: AsyncSession, file_type_id: int
) -> list[ComponentTemplate]:
    return await DatabaseUtils.get_by_filter(
        db, ComponentTemplate, {"file_type_id": file_type_id}
    )


async def get_unique_component_names_by_project(
    db: AsyncSession, project_id: int
) -> list[str]:
    file_type_ids_stmt = select(ProjectFileType.file_type_id).where(
        ProjectFileType.project_id == project_id
    )
    file_type_ids_result = await db.execute(file_type_ids_stmt)
    file_type_ids = [row[0] for row in file_type_ids_result.all()]
    if not file_type_ids:
        return []
    return cast(
        "list[str]",
        await DatabaseUtils.get_distinct_column_values(
            db,
            ComponentTemplate,
            ComponentTemplate.name,
            in_filter=(ComponentTemplate.file_type_id, file_type_ids),
            order_by=ComponentTemplate.name,
        ),
    )


async def delete_orphaned_component_templates(db: AsyncSession) -> int:
    try:
        # Delete ComponentTemplates not referenced by any StandardComponent
        result = await DatabaseUtils.delete_fully_orphaned(
            db, ComponentTemplate, StandardComponent, "id", "component_template_id"
        )
        await db.flush()
        return result
    except Exception:
        await db.rollback()
        raise


async def get_by_id(db: AsyncSession, template_id: int) -> ComponentTemplate | None:
    return await DatabaseUtils.get_by_id(db, ComponentTemplate, "id", template_id)
