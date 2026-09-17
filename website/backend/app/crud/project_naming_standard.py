from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.standard_component import get_components_by_standard
from app.model.project import Project
from app.model.project_file_type import ProjectFileType
from app.model.project_naming_standard import ProjectNamingStandard
from app.schema.responses.project_naming_standard import (
    NamingComponentResponse,
    NamingStandardResponse,
)
from app.utils.database import DatabaseUtils

# --- ProjectNamingStandard CRUD ---


async def get_standards_by_project(
    db: AsyncSession, project_id: int
) -> list[ProjectNamingStandard]:
    return await DatabaseUtils.get_by_filter(
        db, ProjectNamingStandard, {"project_id": project_id}
    )


async def create_standard(
    db: AsyncSession,
    project_id: int,
    name: str,
    project_file_type_id: int,
    pattern: str,
    description: str | None,
) -> ProjectNamingStandard:
    standard = ProjectNamingStandard(
        project_id=project_id,
        name=name,
        project_file_type_id=project_file_type_id,
        pattern=pattern,
        description=description,
    )
    db.add(standard)
    await db.flush()
    return standard


async def delete_standard(db: AsyncSession, standard_id: int) -> int:
    try:
        result = await DatabaseUtils.delete_by_filter(
            db, ProjectNamingStandard, id=standard_id
        )
        await db.flush()
        return result
    except Exception as e:
        await db.rollback()
        raise e


async def get_projects_with_standards(db: AsyncSession) -> list[Project]:
    """Returns all projects that have at least one naming standard."""
    try:
        return await DatabaseUtils.get_all_with_related_exists(
            db,
            Project,
            ProjectNamingStandard,
            related_field="project_id",
            model_field="project_id",
        )
    except Exception as e:
        await db.rollback()
        raise e


async def get_standard_with_components_full(
    db: AsyncSession, standard_id: int
) -> NamingStandardResponse | None:
    """A naming standard with its ordered components and accepted values."""
    standard = await DatabaseUtils.get_by_id(
        db, ProjectNamingStandard, "id", standard_id
    )
    if not standard:
        return None
    project_file_type = await DatabaseUtils.get_by_id(
        db, ProjectFileType, "id", standard.project_file_type_id
    )
    if project_file_type is None:
        return None

    components = [
        NamingComponentResponse(
            id=link.component_template.id,
            name=link.component_template.name,
            description=link.component_template.description,
            regex=link.component_template.regex,
            order=link.order,
            accepted_values=[
                value.value for value in link.component_template.accepted_values
            ],
            project_file_type_id=standard.project_file_type_id,
        )
        for link in await get_components_by_standard(db, standard_id)
        if link.component_template is not None
    ]
    return NamingStandardResponse(
        id=standard.id,
        project_id=standard.project_id,
        name=standard.name,
        project_file_type_id=standard.project_file_type_id,
        file_type_id=project_file_type.file_type_id,
        file_type_name=project_file_type.name,
        pattern=standard.pattern,
        description=standard.description,
        components=components,
    )
