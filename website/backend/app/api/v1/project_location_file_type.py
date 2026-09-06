from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.schema.responses.project_location_file_type import (
    AddFileTypeToLocationResponse,
    FileTypeLocationOut,
    GetFileTypesForLocationResponse,
    RemoveFileTypeFromLocationResponse,
)
from app.service.project_location_file_type import (
    service_add_file_type_to_location,
    service_get_file_types_for_location,
    service_remove_file_type_from_location,
)

router = APIRouter(dependencies=[get_admin_dep])


@router.post(
    "/project/{project_id}/location/{location_id}/filetype/{file_type_id}/add",
    response_model=AddFileTypeToLocationResponse,
)
async def add_file_type(
    project_id: int,
    location_id: int,
    file_type_id: int,
    db: AsyncSession = get_db_dep,
):
    instance = await service_add_file_type_to_location(
        db, project_id, location_id, file_type_id
    )
    return {
        "success": True,
        "file_type": FileTypeLocationOut.model_validate(instance, from_attributes=True),
    }


@router.delete(
    "/project/{project_id}/location/{location_id}/filetype/{file_type_id}/remove",
    response_model=RemoveFileTypeFromLocationResponse,
)
async def remove_file_type(
    project_id: int,
    location_id: int,
    file_type_id: int,
    db: AsyncSession = get_db_dep,
):
    count = await service_remove_file_type_from_location(
        db, project_id, location_id, file_type_id
    )
    return {"success": True, "removed": count}


@router.get(
    "/project/{project_id}/location/{location_id}/filetypes",
    response_model=GetFileTypesForLocationResponse,
)
async def get_file_types(
    project_id: int,
    location_id: int,
    db: AsyncSession = get_db_dep,
):
    file_types = await service_get_file_types_for_location(db, project_id, location_id)
    return {
        "file_types": [
            FileTypeLocationOut.model_validate(ft, from_attributes=True)
            for ft in file_types
        ]
    }
