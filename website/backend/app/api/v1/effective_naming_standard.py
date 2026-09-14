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
    EffectiveNamingStandardOut,
    EffectiveNamingStandardResponse,
    GetEffectiveStandardsResponse,
    GetNamingStandardLocationsResponse,
    NamingStandardLocationOut,
    UnassignEffectiveNamingStandardResponse,
)
from app.service.effective_naming_standard import (
    assign_effective_standard,
    fetch_effective_standards,
    unassign_effective_standard,
)

router = APIRouter(dependencies=[get_admin_dep])


@router.get("/locations", response_model=GetNamingStandardLocationsResponse)
async def get_effective_naming_standard_locations() -> (
    GetNamingStandardLocationsResponse
):
    return GetNamingStandardLocationsResponse(
        locations=[
            NamingStandardLocationOut.model_validate(location)
            for location in EFFECTIVE_NAMING_STANDARD_LOCATIONS
        ]
    )


@router.post(
    "/project/{project_id}/filetype/{project_file_type_id}/assign",
    response_model=EffectiveNamingStandardResponse,
)
async def assign_standard(
    project_id: int,
    project_file_type_id: int,
    payload: AssignEffectiveNamingStandardRequest,
    db: AsyncSession = get_db_dep,
) -> EffectiveNamingStandardResponse:
    result = await assign_effective_standard(
        db,
        project_id,
        project_file_type_id,
        payload.naming_standard_id,
        payload.location_id,
    )
    return EffectiveNamingStandardResponse(
        success=True,
        effective_standard=EffectiveNamingStandardOut.model_validate(
            result, from_attributes=True
        ),
    )


@router.delete(
    "/project/{project_id}/filetype/{project_file_type_id}/location/{location_id}/unassign",
    response_model=UnassignEffectiveNamingStandardResponse,
)
async def unassign_standard(
    project_id: int,
    project_file_type_id: int,
    location_id: int,
    db: AsyncSession = get_db_dep,
) -> UnassignEffectiveNamingStandardResponse:
    await unassign_effective_standard(db, project_id, project_file_type_id, location_id)
    return UnassignEffectiveNamingStandardResponse(success=True)


@router.get(
    "/project/{project_id}/location/{location_id}/effective-standards",
    response_model=GetEffectiveStandardsResponse,
)
async def get_effective_standards_for_location(
    project_id: int, location_id: int, db: AsyncSession = get_db_dep
) -> GetEffectiveStandardsResponse:
    standards = await fetch_effective_standards(db, project_id, location_id)
    return GetEffectiveStandardsResponse(
        effective_standards=[
            EffectiveNamingStandardOut.model_validate(standard, from_attributes=True)
            for standard in standards
        ]
    )
