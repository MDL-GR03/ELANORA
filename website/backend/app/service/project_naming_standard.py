from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud import (
    accepted_value,
    component_accepted_value,
    component_template,
    file_type,
    project_naming_standard,
    standard_component,
)
from app.crud.association import get_project_file_type_by_project_and_file_type
from app.crud.project_naming_standard import get_standard_with_components_full
from app.model.project_file_type import ProjectFileType
from app.schema.responses.project_naming_standard import (
    ImportSelectedStandardsResponse,
    NamingStandardResponse,
    ProjectWithStandardsResponse,
)

logger = get_logger(__name__)


def _is_duplicate_standard_error(error: IntegrityError) -> bool:
    diagnostic = getattr(error.orig, "diag", None)
    return (
        getattr(diagnostic, "constraint_name", None) == "uq_project_filetype_standard"
    )


class ProjectNamingStandardService:
    @staticmethod
    async def get_standards_for_project(db: AsyncSession, project_id: int):
        try:
            standards = await project_naming_standard.get_standards_by_project(
                db, project_id
            )
            return [
                {
                    "id": s.id,
                    "project_id": s.project_id,
                    "name": s.name,
                    "project_file_type_id": s.project_file_type_id,
                    "pattern": s.pattern,
                    "description": s.description,
                }
                for s in standards
            ]
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get project naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_standard_with_components(db: AsyncSession, standard_id: int):
        try:
            return await get_standard_with_components_full(db, standard_id)
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get a naming standard; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def create_standard_with_components(
        db: AsyncSession,
        project_id: int,
        name: str,
        project_file_type_id: int,
        pattern: str,
        description: str | None,
        components: list[dict],
    ):
        try:
            # Block if any regex is empty or only whitespace
            for comp in components:
                regex = comp.get("regex", "")
                if not regex or not str(regex).strip():
                    raise HTTPException(
                        status_code=400,
                        detail="Regex must not be empty for any component.",
                    )
            standard = await project_naming_standard.create_standard(
                db, project_id, name, project_file_type_id, pattern, description
            )
            project_file_type = await db.get(ProjectFileType, project_file_type_id)
            if not project_file_type:
                raise HTTPException(
                    status_code=400, detail="Invalid project_file_type_id"
                )
            file_type_id = project_file_type.file_type_id
            for idx, comp in enumerate(components):
                template = await component_template.get_or_create_component_template(
                    db,
                    file_type_id=file_type_id,
                    name=comp["name"],
                    regex=comp["regex"],
                    description=comp.get("description"),
                )
                await standard_component.link_standard_to_component(
                    db,
                    naming_standard_id=standard.id,
                    component_template_id=template.id,
                    order=comp.get("order", idx + 1),
                )
                for val in comp.get("accepted_values", []):
                    acc_val = await accepted_value.get_or_create_accepted_value(db, val)
                    await component_accepted_value.link_component_to_accepted_value(
                        db, template.id, acc_val.id
                    )
            await db.commit()
            return await ProjectNamingStandardService.get_standard_with_components(
                db, standard.id
            )
        except IntegrityError as e:
            await db.rollback()
            logger.error(
                "Naming standard creation violated data integrity; error_type=%s",
                safe_exception_type(e),
            )
            if _is_duplicate_standard_error(e):
                raise HTTPException(
                    status_code=409,
                    detail="configureNamingStandards.eventMessages.addFailedDuplicate",
                ) from e
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                "Unexpected naming standard creation failure; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def _delete_standard_and_cleanup(db: AsyncSession, standard_id: int):
        logger.info(f"Deleting ProjectNamingStandard with id={standard_id}")
        await project_naming_standard.delete_standard(db, standard_id)
        logger.info(
            "Cleaning up orphaned ComponentAcceptedValue rows for orphaned templates..."
        )
        await component_accepted_value.delete_for_orphaned_templates(db)
        logger.info("Cleaning up orphaned ComponentTemplate rows...")
        await component_template.delete_orphaned_component_templates(db)
        logger.info("Cleaning up orphaned AcceptedValue rows...")
        await accepted_value.delete_orphaned_accepted_values(db)

    @staticmethod
    async def delete_standard(db: AsyncSession, standard_id: int):
        try:
            await ProjectNamingStandardService._delete_standard_and_cleanup(
                db, standard_id
            )
            logger.info("Cleaning up orphaned FileType rows...")
            await file_type.delete_orphaned_file_types(db)
            await db.commit()
            logger.info("Delete and cleanup committed successfully.")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to delete a naming standard; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def delete_all_standards_by_project(db: AsyncSession, project_id: int):
        try:
            standard_ids = await project_naming_standard.get_standards_ids_by_project(
                db, project_id
            )
            for standard_id in standard_ids:
                await ProjectNamingStandardService._delete_standard_and_cleanup(
                    db, standard_id
                )
            logger.info("Bulk delete and cleanup committed successfully.")
        except Exception as e:
            logger.error(
                "Failed to delete project naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_unique_component_names_by_project(db, project_id: int):
        try:
            return await component_template.get_unique_component_names_by_project(
                db, project_id
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get unique component names; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_project_naming_standards_full(db: AsyncSession, project_id: int):
        try:
            standards = await project_naming_standard.get_standards_by_project(
                db, project_id
            )
            standards_with_components = []
            for standard in standards:
                detail = (
                    await ProjectNamingStandardService.get_standard_with_components(
                        db, standard.id
                    )
                )
                standards_with_components.append(detail)
            component_names = (
                await component_template.get_unique_component_names_by_project(
                    db, project_id
                )
            )
            return {
                "component_names": component_names,
                "standards": standards_with_components,
            }
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get complete project naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_projects_with_standards(db: AsyncSession):
        try:
            projects = await project_naming_standard.get_projects_with_standards(db)
            return [
                ProjectWithStandardsResponse(id=p.project_id, name=p.project_name)
                for p in projects
            ]
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get projects with naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def import_selected_standards(
        db: AsyncSession,
        target_project_id: int,
        standard_ids: list[int],
    ):
        try:
            imported_standards = []
            for standard_id in standard_ids:
                # Get the source standard with components
                source_standard = (
                    await ProjectNamingStandardService.get_standard_with_components(
                        db, standard_id
                    )
                )
                if not source_standard:
                    continue

                # Get the file_type_id from the source's project_file_type_id
                source_pft = await db.get(
                    ProjectFileType, source_standard["project_file_type_id"]
                )
                file_type_id = source_pft.file_type_id

                # Use the new CRUD util to get the ProjectFileType for the target project
                target_pft = await get_project_file_type_by_project_and_file_type(
                    db, target_project_id, file_type_id
                )
                if not target_pft:
                    raise HTTPException(
                        status_code=400,
                        detail="Target project does not have the required file type.",
                    )

                # Prepare components for creation (no need to set project_file_type_id in components)
                components = [
                    {
                        "name": c["name"],
                        "regex": c["regex"],
                        "description": c.get("description", ""),
                        "order": c["order"],
                        "accepted_values": c.get("accepted_values", []),
                    }
                    for c in source_standard["components"]
                ]

                # Create the new standard with components from the source standard in the target project
                try:
                    new_standard = await ProjectNamingStandardService.create_standard_with_components(
                        db,
                        target_project_id,
                        source_standard["name"],
                        target_pft.id,
                        source_standard["pattern"],
                        source_standard.get("description", ""),
                        components,
                    )
                    imported_standards.append(NamingStandardResponse(**new_standard))
                except IntegrityError as e:
                    await db.rollback()
                    if _is_duplicate_standard_error(e):
                        raise HTTPException(
                            status_code=409,
                            detail="configureNamingStandards.eventMessages.importFailedDuplicate",
                        ) from e
                    else:
                        logger.error(
                            "Unexpected naming standard import failure; error_type=%s",
                            safe_exception_type(e),
                        )
                        raise

            await db.commit()
            return ImportSelectedStandardsResponse(
                imported_standards=imported_standards
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to import naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise
