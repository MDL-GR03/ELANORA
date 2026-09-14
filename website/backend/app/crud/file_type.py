from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.file_type import FileType
from app.model.project_file_type import ProjectFileType
from app.utils.database import DatabaseUtils


async def get_file_type_by_id(db: AsyncSession, file_type_id: int) -> FileType | None:
    return await DatabaseUtils.get_by_id(db, FileType, "id", file_type_id)


async def get_file_type_by_name(db: AsyncSession, name: str) -> FileType | None:
    return await DatabaseUtils.get_one_by_filter(db, FileType, {"name": name})


async def get_file_type_by_extension(
    db: AsyncSession, extension: str
) -> FileType | None:
    return await DatabaseUtils.get_one_by_filter(db, FileType, {"extension": extension})


async def create_file_type(db: AsyncSession, extension: str) -> FileType:
    file_type = FileType(extension=extension)
    await DatabaseUtils.create(db, file_type)
    await db.flush()
    return file_type


async def update_file_type(
    db: AsyncSession, file_type_id: int, update_fields: dict[str, Any]
) -> int:
    return await DatabaseUtils.update_by_filter(
        db, FileType, {"id": file_type_id}, update_fields
    )


async def delete_file_type(db: AsyncSession, file_type_id: int) -> int:
    return await DatabaseUtils.delete_by_filter(db, FileType, id=file_type_id)


async def delete_orphaned_file_types(db: AsyncSession) -> int:
    """Delete FileType records not referenced by any ProjectFileType."""
    return await DatabaseUtils.delete_fully_orphaned(
        db,
        FileType,
        ProjectFileType,
        main_id_field="id",
        assoc_ref_field="file_type_id",
    )
