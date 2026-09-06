from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.schema.requests.project_naming_standard import (
    CreateNamingStandardRequest,
    ImportSelectedStandardsRequest,
)
from app.schema.responses.project_naming_standard import (
    ImportSelectedStandardsResponse,
    NamingStandardResponse,
    ProjectWithStandardsResponse,
)
from app.service.project_naming_standard import ProjectNamingStandardService

router = APIRouter(dependencies=[get_admin_dep])


@router.get(
    "/projects-with-standards", response_model=list[ProjectWithStandardsResponse]
)
async def get_projects_with_standards(db: AsyncSession = get_db_dep):
    return await ProjectNamingStandardService.get_projects_with_standards(db)


@router.post("/import", response_model=ImportSelectedStandardsResponse)
async def import_selected_standards(
    req: ImportSelectedStandardsRequest,
    db: AsyncSession = get_db_dep,
):
    return await ProjectNamingStandardService.import_selected_standards(
        db, req.target_project_id, req.standard_ids
    )


@router.post("/create", response_model=NamingStandardResponse)
async def create_standard_with_components(
    req: CreateNamingStandardRequest,
    db: AsyncSession = get_db_dep,
):
    components = [c.model_dump() for c in req.components]
    return await ProjectNamingStandardService.create_standard_with_components(
        db,
        req.project_id,
        req.name,
        req.project_file_type_id,
        req.pattern,
        req.description,
        components,
    )


@router.get("/project/{project_id}")
async def get_standards_for_project(project_id: int, db: AsyncSession = get_db_dep):
    return await ProjectNamingStandardService.get_standards_for_project(db, project_id)


@router.get("/{standard_id}")
async def get_standard_with_components(standard_id: int, db: AsyncSession = get_db_dep):
    result = await ProjectNamingStandardService.get_standard_with_components(
        db, standard_id
    )
    if not result:
        raise HTTPException(status_code=404, detail="Standard not found")
    return result


@router.delete("/{standard_id}")
async def delete_standard(standard_id: int, db: AsyncSession = get_db_dep):
    return await ProjectNamingStandardService.delete_standard(db, standard_id)


@router.get("/project/{project_id}/component-names")
async def get_component_names(project_id: int, db: AsyncSession = get_db_dep):
    return await ProjectNamingStandardService.get_unique_component_names_by_project(
        db, project_id
    )


@router.get("/project/{project_id}/full")
async def get_project_naming_standards_full(
    project_id: int, db: AsyncSession = get_db_dep
):
    return await ProjectNamingStandardService.get_project_naming_standards_full(
        db, project_id
    )
