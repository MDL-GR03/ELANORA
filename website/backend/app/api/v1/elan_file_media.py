from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import ProjectAccess, get_project_read_dep
from app.schema.responses.elan_file_media import ProjectFilesWithMediaResponse
from app.service import elan_file_media as elan_media_service

router = APIRouter()


@router.get(
    "/projects/{project_id}/files-with-media",
    response_model=ProjectFilesWithMediaResponse,
)
async def get_project_files_with_media(
    project_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> ProjectFilesWithMediaResponse:
    """Get project files with their associated media for rename suggestions."""
    return await elan_media_service.get_project_files_with_media(db, project_id)
