import secrets

from fastapi import APIRouter, Header, Request, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.cli.bootstrap import BootstrapConfig, bootstrap
from app.core.errors import ElanoraError, ErrorCode
from app.core.limiter import limiter
from app.core.settings import get_settings
from app.dependency.database import get_db_dep
from app.model.instance import Instance
from app.model.user import User
from app.schema.requests.setup import SetupInitializeRequest
from app.schema.responses.instance import InstanceResponse
from app.schema.responses.setup import SetupInitializeResponse, SetupStatusResponse

router = APIRouter()


async def _is_initialized(db: AsyncSession) -> bool:
    instance_count = await db.scalar(select(func.count()).select_from(Instance))
    user_count = await db.scalar(select(func.count()).select_from(User))
    return bool(instance_count or user_count)


@router.get("/status", response_model=SetupStatusResponse)
async def get_setup_status(db: AsyncSession = get_db_dep) -> SetupStatusResponse:
    """Tell the frontend whether one-time setup is still available."""
    token = get_settings().setup_token.get_secret_value()
    return SetupStatusResponse(
        initialized=await _is_initialized(db), setup_token_configured=bool(token)
    )


@router.post(
    "/initialize",
    response_model=SetupInitializeResponse,
    status_code=status.HTTP_201_CREATED,
)
@limiter.limit("5/minute")
async def initialize(
    request: Request,
    body: SetupInitializeRequest,
    db: AsyncSession = get_db_dep,
    setup_token: str | None = Header(default=None, alias="X-ELANORA-Setup-Token"),
) -> SetupInitializeResponse:
    """Create the institution and first administrator exactly once."""
    expected_token = get_settings().setup_token.get_secret_value()
    if not setup_token or not secrets.compare_digest(setup_token, expected_token):
        raise ElanoraError(ErrorCode.SETUP_TOKEN_INVALID)
    if await _is_initialized(db):
        raise ElanoraError(ErrorCode.SETUP_ALREADY_DONE)

    values = body.model_dump(exclude={"password", "password_confirmation"})
    try:
        instance, administrator = await bootstrap(
            db, BootstrapConfig(**values), body.password
        )
    except IntegrityError as error:
        await db.rollback()
        raise ElanoraError(ErrorCode.SETUP_CONCURRENT) from error
    return SetupInitializeResponse(
        instance=InstanceResponse.model_validate(instance, from_attributes=True),
        administrator_username=administrator.username,
    )
