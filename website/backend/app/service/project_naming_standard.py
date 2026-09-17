from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
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
from app.schema.requests.project_naming_standard import NamingComponentRequest
from app.schema.responses.project_naming_standard import (
    ImportSelectedStandardsResponse,
    NamingStandardResponse,
    NamingStandardSummaryResponse,
    ProjectNamingStandardsResponse,
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
    async def get_standards_for_project(
        db: AsyncSession, project_id: int
    ) -> list[NamingStandardSummaryResponse]:
        try:
            standards = await project_naming_standard.get_standards_by_project(
                db, project_id
            )
            return [
                NamingStandardSummaryResponse(
                    id=standard.id,
                    project_id=standard.project_id,
                    name=standard.name,
                    project_file_type_id=standard.project_file_type_id,
                    pattern=standard.pattern,
                    description=standard.description,
                )
                for standard in standards
            ]
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get project naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_standard_with_components(
        db: AsyncSession, standard_id: int
    ) -> NamingStandardResponse | None:
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
        components: list[NamingComponentRequest],
        *,
        commit: bool = True,
    ) -> NamingStandardResponse:
        try:
            if any(not component.regex.strip() for component in components):
                raise ElanoraError(ErrorCode.NAMING_REGEX_EMPTY)
            standard = await project_naming_standard.create_standard(
                db, project_id, name, project_file_type_id, pattern, description
            )
            project_file_type = await db.get(ProjectFileType, project_file_type_id)
            if not project_file_type:
                raise ElanoraError(ErrorCode.PROJECT_FILE_TYPE_INVALID)
            file_type_id = project_file_type.file_type_id
            for component in components:
                template = await component_template.get_or_create_component_template(
                    db,
                    file_type_id=file_type_id,
                    name=component.name,
                    regex=component.regex,
                    description=component.description,
                )
                await standard_component.link_standard_to_component(
                    db,
                    naming_standard_id=standard.id,
                    component_template_id=template.id,
                    order=component.order,
                )
                for val in component.accepted_values or []:
                    acc_val = await accepted_value.get_or_create_accepted_value(db, val)
                    await component_accepted_value.link_component_to_accepted_value(
                        db, template.id, acc_val.id
                    )
            if commit:
                await db.commit()
            created = await ProjectNamingStandardService.get_standard_with_components(
                db, standard.id
            )
            if created is None:
                raise RuntimeError("Created naming standard could not be reloaded")
            return created
        except IntegrityError as e:
            await db.rollback()
            logger.error(
                "Naming standard creation violated data integrity; error_type=%s",
                safe_exception_type(e),
            )
            if _is_duplicate_standard_error(e):
                raise ElanoraError(ErrorCode.NAMING_STANDARD_DUPLICATE) from e
            raise
        except Exception as e:
            await db.rollback()
            logger.error(
                "Unexpected naming standard creation failure; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def _delete_standard_and_cleanup(db: AsyncSession, standard_id: int) -> None:
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
    async def delete_standard(db: AsyncSession, standard_id: int) -> bool:
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
    async def get_unique_component_names_by_project(
        db: AsyncSession, project_id: int
    ) -> list[str]:
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
    async def get_project_naming_standards_full(
        db: AsyncSession, project_id: int
    ) -> ProjectNamingStandardsResponse:
        try:
            standards = await project_naming_standard.get_standards_by_project(
                db, project_id
            )
            standards_with_components: list[NamingStandardResponse] = []
            for standard in standards:
                detail = (
                    await ProjectNamingStandardService.get_standard_with_components(
                        db, standard.id
                    )
                )
                if detail is not None:
                    standards_with_components.append(detail)
            component_names = (
                await component_template.get_unique_component_names_by_project(
                    db, project_id
                )
            )
            return ProjectNamingStandardsResponse(
                component_names=component_names,
                standards=standards_with_components,
            )
        except Exception as e:
            await db.rollback()
            logger.error(
                "Failed to get complete project naming standards; error_type=%s",
                safe_exception_type(e),
            )
            raise

    @staticmethod
    async def get_projects_with_standards(
        db: AsyncSession,
    ) -> list[ProjectWithStandardsResponse]:
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
    ) -> ImportSelectedStandardsResponse:
        try:
            imported_standards: list[NamingStandardResponse] = []
            for standard_id in standard_ids:
                # Get the source standard with components
                source_standard = (
                    await ProjectNamingStandardService.get_standard_with_components(
                        db, standard_id
                    )
                )
                if not source_standard:
                    raise ElanoraError(ErrorCode.NAMING_STANDARD_NOT_FOUND)

                # Get the file_type_id from the source's project_file_type_id
                source_pft = await db.get(
                    ProjectFileType, source_standard.project_file_type_id
                )
                if source_pft is None:
                    raise ElanoraError(ErrorCode.NAMING_SOURCE_FILE_TYPE_INVALID)
                file_type_id = source_pft.file_type_id

                # Use the new CRUD util to get the ProjectFileType for the target project
                target_pft = await get_project_file_type_by_project_and_file_type(
                    db, target_project_id, file_type_id
                )
                if not target_pft:
                    raise ElanoraError(ErrorCode.NAMING_TARGET_FILE_TYPE_MISSING)

                # Prepare components for creation (no need to set project_file_type_id in components)
                components = [
                    NamingComponentRequest(
                        name=component.name,
                        regex=component.regex,
                        description=component.description,
                        order=component.order,
                        accepted_values=component.accepted_values,
                        project_file_type_id=target_pft.id,
                    )
                    for component in source_standard.components
                ]

                # Create the new standard with components from the source standard in the target project
                try:
                    new_standard = await ProjectNamingStandardService.create_standard_with_components(
                        db,
                        target_project_id,
                        source_standard.name,
                        target_pft.id,
                        source_standard.pattern,
                        source_standard.description,
                        components,
                        commit=False,
                    )
                    imported_standards.append(new_standard)
                except IntegrityError as e:
                    await db.rollback()
                    if _is_duplicate_standard_error(e):
                        raise ElanoraError(
                            ErrorCode.NAMING_STANDARD_IMPORT_DUPLICATE
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
