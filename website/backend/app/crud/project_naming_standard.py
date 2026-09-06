from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.standard_component import get_components_by_standard
from app.model.project import Project
from app.model.project_file_type import ProjectFileType
from app.model.project_naming_standard import ProjectNamingStandard
from app.utils.database import DatabaseUtils

# --- ProjectNamingStandard CRUD ---


async def get_standards_by_project(
    db: AsyncSession, project_id: int
) -> list[ProjectNamingStandard]:
    return await DatabaseUtils.get_by_filter(
        db, ProjectNamingStandard, {"project_id": project_id}
    )


async def get_standards_ids_by_project(db: AsyncSession, project_id: int) -> list[int]:
    standards = await get_standards_by_project(db, project_id)
    return [standard.id for standard in standards]


async def get_standard_by_id(
    db: AsyncSession, standard_id: int
) -> ProjectNamingStandard | None:
    return await DatabaseUtils.get_by_id(db, ProjectNamingStandard, "id", standard_id)


async def create_standard(
    db: AsyncSession,
    project_id: int,
    name: str,
    project_file_type_id: int,
    pattern: str,
    description: str | None,
):
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


async def get_standards_by_ids(
    db: AsyncSession, ids: list[int]
) -> list[ProjectNamingStandard]:
    """Returns all ProjectNamingStandard objects matching the given ids."""
    try:
        return await DatabaseUtils.get_by_filter(db, ProjectNamingStandard, {"id": ids})
    except Exception as e:
        await db.rollback()
        raise e


async def get_standard_with_components_full(db, standard_id: int):
    # Get the standard
    standard = await DatabaseUtils.get_by_id(
        db, ProjectNamingStandard, "id", standard_id
    )
    if not standard:
        return None

    # Get the project_file_type
    project_file_type = await DatabaseUtils.get_by_id(
        db, ProjectFileType, "id", standard.project_file_type_id
    )

    # Eagerly load components, templates, and accepted values
    std_components = await get_components_by_standard(db, standard_id)
    components = []
    for sc in std_components:
        template = sc.component_template
        accepted_values = (
            [v.value for v in template.accepted_values] if template else []
        )
        components.append(
            {
                "id": template.id if template else None,
                "name": template.name if template else None,
                "description": template.description if template else None,
                "regex": template.regex if template else None,
                "order": sc.order,
                "accepted_values": accepted_values,
                "project_file_type_id": standard.project_file_type_id,
            }
        )

    return {
        "id": standard.id,
        "project_id": standard.project_id,
        "name": standard.name,
        "project_file_type_id": standard.project_file_type_id,
        "file_type_id": project_file_type.file_type_id if project_file_type else None,
        "file_type_name": project_file_type.name if project_file_type else None,
        "pattern": standard.pattern,
        "description": standard.description,
        "components": components,
    }
