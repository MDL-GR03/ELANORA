from sqlalchemy.ext.asyncio import AsyncSession

from app.crud import elan_file_media as elan_media_crud
from app.schema.responses.elan_file_media import (
    ElanFileWithMediaResponse,
    ProjectFilesWithMediaResponse,
)


async def get_project_files_with_media(
    db: AsyncSession, project_id: int
) -> ProjectFilesWithMediaResponse:
    """Get project files with their associated media for rename suggestions."""
    files_data = await elan_media_crud.get_project_files_with_media_simple(
        db, project_id
    )
    files_with_media = [
        ElanFileWithMediaResponse(
            elan_id=file_data["elan_id"],
            filename=file_data["filename"],
            file_path=file_data["file_path"],
            media_filenames=file_data["media_filenames"],
        )
        for file_data in files_data
    ]
    return ProjectFilesWithMediaResponse(files=files_with_media)
