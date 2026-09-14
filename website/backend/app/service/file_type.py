from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
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
    get_file_type_by_id,
)

logger = get_logger(__name__)


class FileTypeService:
    @staticmethod
    async def create_file_type(db, name: str, extension: str):
        try:
            file_type = await file_type_crud.create_file_type(db, name, extension)
            await db.commit()
            return file_type
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def update_file_type(db, file_type_id: int, update_fields: dict):
        try:
            await file_type_crud.update_file_type(db, file_type_id, update_fields)
            await db.commit()
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def delete_file_type(db, file_type_id: int):
        try:
            await file_type_crud.delete_file_type(db, file_type_id)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            # Check for the specific constraint name
            if "fk_project_file_type" in str(exc.orig):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "file_type_in_use",
                        "message": "Cannot delete: This file type is used by a naming standard or component. Please delete the related naming standard first.",
                    },
                ) from exc
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def create_file_type_for_project(
        db, name: str, extension: str, project_id: int
    ):
        # Get or create the global FileType (by extension)
        file_type = await get_file_type_by_extension(db, extension)
        if not file_type:
            file_type = await create_file_type(db, extension=extension)
        # Check for existing ProjectFileType with same name in this project
        project_types = await get_project_file_types(db, project_id)
        if any(pt.name == name for pt in project_types):
            raise HTTPException(
                status_code=409, detail="File type name already exists in this project"
            )
        # Create the ProjectFileType association
        project_file_type = await add_project_file_type(
            db, project_id, name, file_type.id
        )
        await db.commit()
        # Fetch the related FileType for the extension
        file_type = await get_file_type_by_id(db, project_file_type.file_type_id)
        # Return a dict or a Pydantic model
        return {
            "id": project_file_type.id,
            "name": project_file_type.name,
            "extension": file_type.extension,
            "project_id": project_file_type.project_id,
            "file_type_id": project_file_type.file_type_id,
        }

    @staticmethod
    async def get_file_types_for_project(db, project_id: int):
        return await get_project_file_types(db, project_id)

    @staticmethod
    async def add_existing_file_type_to_project(
        db, file_type_id: int, project_id: int, name: str
    ):
        file_type = await get_file_type_by_id(db, file_type_id)
        if not file_type:
            raise HTTPException(status_code=404, detail="File type not found")
        try:
            await add_project_file_type(db, project_id, name, file_type_id)
            await db.commit()
            return file_type
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def import_project_file_type(
        db, target_project_id: int, name: str, file_type_id: int
    ):
        """Create a new ProjectFileType in the target project, using an existing FileType."""
        try:
            project_file_type = await add_project_file_type(
                db, target_project_id, name, file_type_id
            )
            await db.commit()
            # Use the CRUD function to reload with relationship
            refreshed = await get_project_file_type_with_file_type(
                db, project_file_type.id
            )
            return refreshed
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def import_selected_file_types(
        db, source_project_id: int, target_project_id: int, file_type_names: list[str]
    ):
        """Import selected file types (by name) from source_project_id to target_project_id."""
        source_types = await FileTypeService.get_file_types_for_project(
            db, source_project_id
        )
        imported = []
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
        db, project_file_type_id: int, project_id: int
    ):
        pft = await get_project_file_type_by_id(db, project_file_type_id)
        if not pft:
            raise HTTPException(status_code=404, detail="Project file type not found")
        try:
            await delete_project_file_type(db, project_file_type_id, project_id)
            await db.commit()
            # Clean up orphaned FileTypes
            await delete_orphaned_file_types(db)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            if "fk_project_file_type" in str(exc.orig):
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "file_type_in_use",
                        "message": "Cannot delete: This file type is used by a naming standard or component. Please delete the related naming standard first.",
                    },
                ) from exc
            raise
        except Exception:
            await db.rollback()
            raise

    @staticmethod
    async def update_project_file_type(
        db, project_id: int, project_file_type_id: int, update_fields: dict
    ):
        pft = await get_project_file_type_by_id(db, project_file_type_id)
        if not pft:
            raise HTTPException(status_code=404, detail="Project file type not found")
        if pft.project_id != project_id:
            raise HTTPException(
                status_code=403, detail="File type does not belong to this project"
            )

        # Update name if present
        if "name" in update_fields:
            await update_project_file_type_name(
                db, project_file_type_id, update_fields["name"]
            )

        # Update extension if present
        if "extension" in update_fields:
            new_ext = update_fields["extension"]
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

        updated_pft = await get_project_file_type_by_id(db, project_file_type_id)
        if not updated_pft:
            raise HTTPException(
                status_code=404, detail="Project file type not found after update"
            )
        return {
            "id": updated_pft.id,
            "name": updated_pft.name,
            "extension": updated_pft.file_type.extension
            if updated_pft.file_type
            else None,
            "file_type_id": updated_pft.file_type_id,
        }
