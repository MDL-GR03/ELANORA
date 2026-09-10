"""Institution administrator operational health API."""

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep
from app.model.user import User
from app.schema.responses.operations import (
    OperationsStatusResponse,
    StorageCheckResponse,
)
from app.service.operations import check_storage, operations_status

router = APIRouter()


@router.get("/status", response_model=OperationsStatusResponse)
async def get_operations_status(
    db: AsyncSession = get_db_dep,
    _administrator: User = get_admin_dep,
) -> OperationsStatusResponse:
    return await operations_status(db)


@router.post("/storage-check", response_model=StorageCheckResponse)
def run_storage_check(
    _administrator: User = get_admin_dep,
) -> StorageCheckResponse:
    return check_storage()
