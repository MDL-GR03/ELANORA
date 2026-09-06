from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.schema.requests.file_type import (
    FileTypeCreateRequest,
    FileTypeImportSelectedRequest,
    FileTypeUpdateRequest,
)
from app.schema.responses.file_type import FileTypeResponse
from app.service.file_type import FileTypeService

router = APIRouter(dependencies=[get_admin_dep])


@router.get("/project/{project_id}", response_model=list[FileTypeResponse])
async def get_file_types_for_project(project_id: int, db: AsyncSession = get_db_dep):
    project_file_types = await FileTypeService.get_file_types_for_project(
        db, project_id
    )
    result = []
    for pft in project_file_types:
        # Make sure file_type is loaded
        extension = pft.file_type.extension if pft.file_type else None
        result.append(
            FileTypeResponse(
                id=pft.id,
                name=pft.name,
                extension=extension,
                file_type_id=pft.file_type_id if pft.file_type else None,
            )
        )
    return result


@router.delete(
    "/project/{project_id}/file_type/{project_file_type_id}",
    response_model=FileTypeResponse,
)
async def remove_file_type_from_project(
    project_id: int, project_file_type_id: int, db: AsyncSession = get_db_dep
):
    # Fetch before delete for response
    project_file_types = await FileTypeService.get_file_types_for_project(
        db, project_id
    )
    ft = next((ft for ft in project_file_types if ft.id == project_file_type_id), None)
    if not ft:
        raise HTTPException(status_code=404, detail="File type not found in project")
    extension = ft.file_type.extension if ft.file_type else None

    # Actually delete the association
    await FileTypeService.remove_file_type_from_project(
        db, project_file_type_id, project_id
    )

    return FileTypeResponse(
        id=ft.id,
        name=ft.name,
        extension=extension,
        file_type_id=ft.file_type_id if ft.file_type else None,
    )


@router.get("/import_preview/", response_model=list[FileTypeResponse])
async def preview_importable_file_types(
    source_project_id: int, target_project_id: int, db: AsyncSession = get_db_dep
):
    """Returns file types from source_project_id, and marks which already exist in target_project_id."""
    source_types = await FileTypeService.get_file_types_for_project(
        db, source_project_id
    )
    target_types = await FileTypeService.get_file_types_for_project(
        db, target_project_id
    )
    target_names = {ft.name for ft in target_types}
    result = []
    for ft in source_types:
        result.append(
            FileTypeResponse(
                id=ft.id,
                name=ft.name,
                extension=ft.extension,
                file_type_id=ft.file_type_id,
                exists_in_target=ft.name in target_names,
            )
        )
    return result


@router.post("/import_selected/", response_model=list[FileTypeResponse])
async def import_selected_file_types(
    source_project_id: int,
    target_project_id: int,
    req: FileTypeImportSelectedRequest,
    db: AsyncSession = get_db_dep,
):
    imported = await FileTypeService.import_selected_file_types(
        db, source_project_id, target_project_id, req.file_type_names
    )
    return [
        FileTypeResponse(
            id=ft.id,
            name=ft.name,
            extension=ft.file_type.extension
            if hasattr(ft, "file_type")
            else ft.extension,
            file_type_id=ft.file_type_id if hasattr(ft, "file_type") else None,
            exists_in_target=False,
        )
        for ft in imported
    ]


@router.post("/project/{project_id}/add", response_model=FileTypeResponse)
async def add_project_file_type(
    project_id: int, req: FileTypeCreateRequest, db: AsyncSession = get_db_dep
):
    result = await FileTypeService.create_file_type_for_project(
        db, req.name, req.extension, project_id
    )
    return FileTypeResponse(
        id=result["id"],
        name=result["name"],
        extension=result["extension"],
        file_type_id=result.get("file_type_id"),
        exists_in_target=result.get("exists_in_target", False),
    )


@router.put(
    "/project/{project_id}/file_type/{project_file_type_id}",
    response_model=FileTypeResponse,
)
async def update_project_file_type(
    project_id: int,
    project_file_type_id: int,
    update: FileTypeUpdateRequest,
    db: AsyncSession = get_db_dep,
):
    result = await FileTypeService.update_project_file_type(
        db, project_id, project_file_type_id, update.model_dump(exclude_unset=True)
    )
    return FileTypeResponse(
        id=result["id"],
        name=result["name"],
        extension=result["extension"],
        file_type_id=result.get("file_type_id"),
    )
