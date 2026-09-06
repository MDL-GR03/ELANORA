from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.effective_naming_standard_locations import (
    EFFECTIVE_NAMING_STANDARD_LOCATIONS,
)
from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.schema.requests.effective_naming_standard import (
    AssignEffectiveNamingStandardRequest,
)
from app.schema.responses.effective_naming_standard import (
    EffectiveNamingStandardResponse,
    GetEffectiveStandardsResponse,
    UnassignEffectiveNamingStandardResponse,
)
from app.service.effective_naming_standard import (
    assign_effective_standard,
    fetch_effective_standards,
    unassign_effective_standard,
)

router = APIRouter(dependencies=[get_admin_dep])


@router.get("/locations")
async def get_effective_naming_standard_locations():
    return {"locations": EFFECTIVE_NAMING_STANDARD_LOCATIONS}


@router.post(
    "/project/{project_id}/filetype/{project_file_type_id}/assign",
    response_model=EffectiveNamingStandardResponse,
)
async def assign_standard(
    project_id: int,
    project_file_type_id: int,
    payload: AssignEffectiveNamingStandardRequest,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    result = await assign_effective_standard(
        db,
        project_id,
        project_file_type_id,
        payload.naming_standard_id,
        payload.location_id,
    )
    return {"success": True, "effective_standard": result}


@router.delete(
    "/project/{project_id}/filetype/{project_file_type_id}/location/{location_id}/unassign",
    response_model=UnassignEffectiveNamingStandardResponse,
)
async def unassign_standard(
    project_id: int,
    project_file_type_id: int,
    location_id: int,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    await unassign_effective_standard(db, project_id, project_file_type_id, location_id)
    return {"success": True}


@router.get(
    "/project/{project_id}/location/{location_id}/effective-standards",
    response_model=GetEffectiveStandardsResponse,
)
async def get_effective_standards_for_location(
    project_id: int, location_id: int, db: AsyncSession = get_db_dep
):
    standards = await fetch_effective_standards(db, project_id, location_id)
    return {"effective_standards": standards}
