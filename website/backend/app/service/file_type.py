from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.core.errors import ElanoraError, ErrorCode
from app.crud import file_type as file_type_crud
from app.crud.association import (
    add_project_file_type,
    count_project_file_types_by_file_type_id,
    delete_project_file_type,
    get_project_file_type_by_id,
    get_project_file_type_with_file_type,
    get_project_file_types,
    update_project_file_type_file_type_id,
    update_project_file_type_name,
)
from app.crud.file_type import (
    create_file_type,
    delete_orphaned_file_types,
    get_file_type_by_extension,
)
from app.model.file_type import FileType
from app.model.project_file_type import ProjectFileType

logger = get_logger(__name__)


class FileTypeService:
    @staticmethod
    async def create_file_type(db: AsyncSession, name: str, extension: str) -> FileType:
        try:
            # FileType is global and stores only the extension. The display name
            # belongs to the project-specific ProjectFileType association.
            file_type = await file_type_crud.create_file_type(db, extension)
            await db.commit()
            return file_type
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def update_file_type(
        db: AsyncSession, file_type_id: int, update_fields: dict[str, Any]
    ) -> None:
        try:
            await file_type_crud.update_file_type(db, file_type_id, update_fields)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_file_type(db: AsyncSession, file_type_id: int) -> None:
        try:
            await file_type_crud.delete_file_type(db, file_type_id)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # Check for the specific constraint name
            if "fk_project_file_type" in str(exc.orig):
                raise ElanoraError(ErrorCode.FILE_TYPE_IN_USE) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def create_file_type_for_project(
        db: AsyncSession, name: str, extension: str, project_id: int
    ) -> ProjectFileType:
        # Get or create the global FileType (by extension)
        file_type = await get_file_type_by_extension(db, extension)
        if not file_type:
            file_type = await create_file_type(db, extension=extension)
        # Check for existing ProjectFileType with same name in this project
        project_types = await get_project_file_types(db, project_id)
        if any(pt.name == name for pt in project_types):
            raise ElanoraError(ErrorCode.FILE_TYPE_NAME_EXISTS)
        project_file_type = await add_project_file_type(
            db, project_id, name, file_type.id
        )
        await db.commit()
        return await FileTypeService._reloaded(db, project_file_type.id)

    @staticmethod
    async def _reloaded(db: AsyncSession, project_file_type_id: int) -> ProjectFileType:
        """A project file type with its global file type loaded."""
        reloaded = await get_project_file_type_with_file_type(db, project_file_type_id)
        if reloaded is None:
            raise ElanoraError(ErrorCode.FILE_TYPE_NOT_FOUND)
        return reloaded

    @staticmethod
    async def get_file_types_for_project(
        db: AsyncSession, project_id: int
    ) -> list[ProjectFileType]:
        return await get_project_file_types(db, project_id)

    @staticmethod
    async def import_project_file_type(
        db: AsyncSession, target_project_id: int, name: str, file_type_id: int
    ) -> ProjectFileType:
        """Create a new ProjectFileType in the target project, using an existing FileType."""
        try:
            project_file_type = await add_project_file_type(
                db, target_project_id, name, file_type_id
            )
            await db.commit()
            return await FileTypeService._reloaded(db, project_file_type.id)
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def import_selected_file_types(
        db: AsyncSession,
        source_project_id: int,
        target_project_id: int,
        file_type_names: list[str],
    ) -> list[ProjectFileType]:
        """Import selected file types (by name) from source_project_id to target_project_id."""
        source_types = await FileTypeService.get_file_types_for_project(
            db, source_project_id
        )
        imported: list[ProjectFileType] = []
        for ft in source_types:
            if ft.name in file_type_names:
                try:
                    new_pft = await FileTypeService.import_project_file_type(
                        db, target_project_id, ft.name, ft.file_type_id
                    )
                    imported.append(new_pft)
                except Exception as error:
                    logger.error(
                        "Failed to import a project file type; error_type=%s",
                        safe_exception_type(error),
                    )
                    continue
        return imported

    @staticmethod
    async def remove_file_type_from_project(
        db: AsyncSession, project_file_type_id: int, project_id: int
    ) -> None:
        pft = await get_project_file_type_by_id(db, project_file_type_id)
        if not pft:
            raise ElanoraError(ErrorCode.FILE_TYPE_NOT_FOUND)
        try:
            await delete_project_file_type(db, project_file_type_id, project_id)
            await db.commit()
            # Clean up orphaned FileTypes
            await delete_orphaned_file_types(db)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            if "fk_project_file_type" in str(exc.orig):
                raise ElanoraError(ErrorCode.FILE_TYPE_IN_USE) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def update_project_file_type(
        db: AsyncSession,
        project_id: int,
        project_file_type_id: int,
        update_fields: dict[str, str | None],
    ) -> ProjectFileType:
        pft = await get_project_file_type_by_id(db, project_file_type_id)
        if not pft:
            raise ElanoraError(ErrorCode.FILE_TYPE_NOT_FOUND)
        if pft.project_id != project_id:
            raise ElanoraError(ErrorCode.FILE_TYPE_FOREIGN)

        # Update name if present
        new_name = update_fields.get("name")
        if new_name is not None:
            await update_project_file_type_name(db, project_file_type_id, new_name)

        # Update extension if present
        new_ext = update_fields.get("extension")
        if new_ext is not None:
            # Check if a FileType with this extension already exists
            existing_ft = await get_file_type_by_extension(db, new_ext)
            if existing_ft:
                # Point this ProjectFileType to the existing FileType
                await update_project_file_type_file_type_id(
                    db, project_file_type_id, existing_ft.id
                )
            else:
                count = await count_project_file_types_by_file_type_id(
                    db, pft.file_type_id
                )
                if count == 1:
                    # Safe to update the extension directly
                    await file_type_crud.update_file_type(
                        db, pft.file_type_id, {"extension": new_ext}
                    )
                else:
                    # Create a new FileType and point to it
                    new_ft = await file_type_crud.create_file_type(db, new_ext)
                    await update_project_file_type_file_type_id(
                        db, project_file_type_id, new_ft.id
                    )

        await db.commit()

        return await FileTypeService._reloaded(db, project_file_type_id)
