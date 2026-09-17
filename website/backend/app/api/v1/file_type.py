from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.model.project_file_type import ProjectFileType
from app.schema.requests.file_type import (
    FileTypeCreateRequest,
    FileTypeImportSelectedRequest,
    FileTypeUpdateRequest,
)
from app.schema.responses.file_type import FileTypeResponse
from app.service.file_type import FileTypeService

router = APIRouter(dependencies=[get_admin_dep])


def _response(
    project_file_type: ProjectFileType, *, exists_in_target: bool = False
) -> FileTypeResponse:
    return FileTypeResponse(
        id=project_file_type.id,
        name=project_file_type.name,
        extension=project_file_type.file_type.extension,
        file_type_id=project_file_type.file_type_id,
        exists_in_target=exists_in_target,
    )


@router.get("/project/{project_id}", response_model=list[FileTypeResponse])
async def get_file_types_for_project(
    project_id: int, db: AsyncSession = get_db_dep
) -> list[FileTypeResponse]:
    project_file_types = await FileTypeService.get_file_types_for_project(
        db, project_id
    )
    return [_response(item) for item in project_file_types]


@router.delete(
    "/project/{project_id}/file_type/{project_file_type_id}",
    response_model=FileTypeResponse,
)
async def remove_file_type_from_project(
    project_id: int, project_file_type_id: int, db: AsyncSession = get_db_dep
) -> FileTypeResponse:
    project_file_types = await FileTypeService.get_file_types_for_project(
        db, project_id
    )
    removed = next(
        (item for item in project_file_types if item.id == project_file_type_id),
        None,
    )
    if removed is None:
        raise ElanoraError(ErrorCode.FILE_TYPE_NOT_FOUND)
    response = _response(removed)
    await FileTypeService.remove_file_type_from_project(
        db, project_file_type_id, project_id
    )
    return response


@router.get("/import_preview/", response_model=list[FileTypeResponse])
async def preview_importable_file_types(
    source_project_id: int, target_project_id: int, db: AsyncSession = get_db_dep
) -> list[FileTypeResponse]:
    """File types of the source project, marking those the target already has."""
    source_types = await FileTypeService.get_file_types_for_project(
        db, source_project_id
    )
    target_types = await FileTypeService.get_file_types_for_project(
        db, target_project_id
    )
    target_names = {item.name for item in target_types}
    return [
        _response(item, exists_in_target=item.name in target_names)
        for item in source_types
    ]


@router.post("/import_selected/", response_model=list[FileTypeResponse])
async def import_selected_file_types(
    source_project_id: int,
    target_project_id: int,
    req: FileTypeImportSelectedRequest,
    db: AsyncSession = get_db_dep,
) -> list[FileTypeResponse]:
    imported = await FileTypeService.import_selected_file_types(
        db, source_project_id, target_project_id, req.file_type_names
    )
    return [_response(item) for item in imported]


@router.post("/project/{project_id}/add", response_model=FileTypeResponse)
async def add_project_file_type(
    project_id: int, req: FileTypeCreateRequest, db: AsyncSession = get_db_dep
) -> FileTypeResponse:
    created = await FileTypeService.create_file_type_for_project(
        db, req.name, req.extension, project_id
    )
    return _response(created)


@router.put(
    "/project/{project_id}/file_type/{project_file_type_id}",
    response_model=FileTypeResponse,
)
async def update_project_file_type(
    project_id: int,
    project_file_type_id: int,
    update: FileTypeUpdateRequest,
    db: AsyncSession = get_db_dep,
) -> FileTypeResponse:
    updated = await FileTypeService.update_project_file_type(
        db, project_id, project_file_type_id, update.model_dump(exclude_unset=True)
    )
    return _response(updated)
