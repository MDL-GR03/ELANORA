from typing import Annotated

from fastapi import APIRouter, Depends, File, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.core.limiter import limiter
from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep, get_admin_user_dep
from app.model.instance import Instance
from app.model.user import User
from app.schema.requests.setup import InstanceBrandingUpdateRequest, InstanceSettingsUpdateRequest
from app.schema.responses.instance import InstanceResponse
from app.service import instance as instance_service
from app.service.instance_assets import MAX_UPLOAD_BYTES, read_logo, replace_logo

router = APIRouter()


@router.get("/", response_model=InstanceResponse | None)
async def get_instance(
    db: AsyncSession = get_db_dep,
    current_user: User = get_admin_user_dep,
) -> InstanceResponse | None:
    """Return the instance configuration for administrators.
    
    Returns the full instance configuration including all settings.
    Only available to administrators.
    """
    instance = await db.scalar(select(Instance))
    return (
        InstanceResponse.model_validate(instance, from_attributes=True)
        if instance is not None
        else None
    )


@router.get("/info", response_model=InstanceResponse | None)
async def get_instance_info(
    db: AsyncSession = get_db_dep,
) -> InstanceResponse | None:
    """Return the public profile for this single-institution installation."""
    instance = await instance_service.get_instance_info(db)
    return (
        InstanceResponse.model_validate(instance, from_attributes=True)
        if instance is not None
        else None
    )


@router.patch("/branding", response_model=InstanceResponse)
async def update_instance_branding(
    body: InstanceBrandingUpdateRequest,
    db: AsyncSession = get_db_dep,
    administrator: User = get_admin_dep,
) -> InstanceResponse:
    """Update institution identity and theme as the installation administrator."""
    instance = await instance_service.update_instance(
        db,
        administrator.instance_id,
        body.model_dump(exclude_none=True),
    )
    if instance is None:
        raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)
    return InstanceResponse.model_validate(instance, from_attributes=True)


@router.patch("/settings", response_model=InstanceResponse)
@limiter.limit("5/minute")
async def update_instance_settings(
    body: InstanceSettingsUpdateRequest,
    db: AsyncSession = get_db_dep,
    administrator: User = get_admin_dep,
) -> InstanceResponse:
    """Update general system settings as the installation administrator.
    
    Allows modification of database-level configuration such as:
    - Domain name
    - Timezone
    - Default language
    - Maximum file size
    - Maximum number of users
    - Installation active status
    
    Rate limited to prevent abuse.
    """
    instance = await db.get(Instance, administrator.instance_id)
    if instance is None:
        raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)
    
    # Build update data
    update_data = body.model_dump(exclude_none=True)
    
    # Convert Decimal to float for max_file_size_mb if present
    if "max_file_size_mb" in update_data:
        update_data["max_file_size_mb"] = float(update_data["max_file_size_mb"])
    
    # Update the instance
    updated_instance = await instance_service.update_instance(
        db,
        administrator.instance_id,
        update_data,
    )
    
    if updated_instance is None:
        raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)
    
    return InstanceResponse.model_validate(updated_instance, from_attributes=True)


@router.put("/logo", status_code=204)
async def upload_instance_logo(
    logo: Annotated[UploadFile, File()],
    db: AsyncSession = get_db_dep,
    administrator: User = get_admin_dep,
) -> Response:
    """Validate, normalize, and persist a new institution logo."""
    content = await logo.read(MAX_UPLOAD_BYTES + 1)
    instance = await db.get(Instance, administrator.instance_id)
    if instance is None:
        raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)
    try:
        await replace_logo(db, instance, administrator, content)
    except ValueError as error:
        raise ElanoraError(ErrorCode.LOGO_INVALID) from error
    return Response(status_code=204)


@router.get("/logo")
async def get_instance_logo(db: AsyncSession = get_db_dep) -> Response:
    """Return the current normalized logo with immutable-safe caching semantics."""
    instance = await db.scalar(select(Instance))
    if instance is None:
        raise ElanoraError(ErrorCode.INSTITUTION_NOT_FOUND)
    content = await read_logo(db, instance)
    if content is None:
        raise ElanoraError(ErrorCode.LOGO_NOT_CONFIGURED)
    return Response(
        content=content,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=300"},
    )
