from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.model.instance import Instance
from app.model.user import User
from app.schema.requests.setup import InstanceBrandingUpdateRequest
from app.schema.responses.instance import InstanceResponse
from app.service import instance as instance_service
from app.service.instance_assets import MAX_UPLOAD_BYTES, read_logo, replace_logo

router = APIRouter()


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
        raise HTTPException(status_code=404, detail="Institution not found")
    return InstanceResponse.model_validate(instance, from_attributes=True)


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
        raise HTTPException(status_code=404, detail="Institution not found")
    try:
        await replace_logo(db, instance, administrator, content)
    except ValueError as error:
        raise HTTPException(
            status_code=422, detail="Invalid institution logo"
        ) from error
    return Response(status_code=204)


@router.get("/logo")
async def get_instance_logo(db: AsyncSession = get_db_dep) -> Response:
    """Return the current normalized logo with immutable-safe caching semantics."""
    instance = await db.scalar(select(Instance))
    if instance is None:
        raise HTTPException(status_code=404, detail="Institution not found")
    content = await read_logo(db, instance)
    if content is None:
        raise HTTPException(status_code=404, detail="Institution logo not configured")
    return Response(
        content=content,
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=300"},
    )
