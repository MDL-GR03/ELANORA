"""Project-scoped protocol governance and validation endpoints."""

import uuid

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
    get_protocol_manager_dep,
)
from app.model.enums import ProjectCapability
from app.schema.protocol import (
    ArchiveProtocolVersionRequest,
    CapabilityGrantResponse,
    ComplianceScanResponse,
    CorpusProtocolSuggestionResponse,
    CreateProtocolRequest,
    CreateProtocolVersionRequest,
    ProtocolResponse,
    ProtocolVersionResponse,
    UpdateProtocolDraftRequest,
    ValidationRunResponse,
)
from app.service import protocol as protocol_service

router = APIRouter()


def _domain_http_error(error: Exception) -> HTTPException:
    # Pydantic's ValidationError is a ValueError. Serializing a response badly
    # is a fault in ELANORA, not a conflicting request.
    if isinstance(error, PydanticValidationError):
        raise error
    if isinstance(error, protocol_service.ProtocolNotFoundError):
        return HTTPException(status_code=404, detail="Protocol not found")
    return HTTPException(status_code=409, detail="Protocol state conflict")


@router.get("/projects/{project_id}/protocols", response_model=list[ProtocolResponse])
async def list_protocols(
    access: ProjectAccess = get_project_read_dep,
    db: AsyncSession = get_db_dep,
) -> list[ProtocolResponse]:
    protocols = await protocol_service.list_protocols(db, access.project)
    return [ProtocolResponse.model_validate(item) for item in protocols]


@router.get(
    "/projects/{project_id}/protocol-suggestions",
    response_model=CorpusProtocolSuggestionResponse,
)
async def suggest_protocol(
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> CorpusProtocolSuggestionResponse:
    """Infer an advisory draft from each file's latest accepted revision."""
    return await protocol_service.suggest_protocol_from_corpus(db, access.project)


@router.post(
    "/projects/{project_id}/protocols",
    response_model=ProtocolResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_protocol(
    request: CreateProtocolRequest,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolResponse:
    try:
        protocol = await protocol_service.create_protocol(
            db,
            project=access.project,
            name=request.name,
            description=request.description,
            rules=request.rules,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return ProtocolResponse.model_validate(protocol)
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A protocol with this name already exists",
        ) from error


@router.post(
    "/projects/{project_id}/protocols/{protocol_id}/versions",
    response_model=ProtocolVersionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_version(
    protocol_id: uuid.UUID,
    request: CreateProtocolVersionRequest,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolVersionResponse:
    try:
        version = await protocol_service.create_protocol_version(
            db,
            project=access.project,
            protocol_id=protocol_id,
            rules=request.rules,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return ProtocolVersionResponse.model_validate(version)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.put(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}",
    response_model=ProtocolVersionResponse,
)
async def update_draft(
    protocol_version_id: uuid.UUID,
    request: UpdateProtocolDraftRequest,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolVersionResponse:
    try:
        version = await protocol_service.update_draft(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            rules=request.rules,
        )
        await db.commit()
        return ProtocolVersionResponse.model_validate(version)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.post(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}/publish",
    response_model=ProtocolVersionResponse,
)
async def publish_version(
    protocol_version_id: uuid.UUID,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolVersionResponse:
    try:
        version = await protocol_service.publish_protocol_version(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return ProtocolVersionResponse.model_validate(version)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.put(
    "/projects/{project_id}/protocol-version/{protocol_version_id}",
    response_model=ProtocolVersionResponse,
)
async def pin_version(
    protocol_version_id: uuid.UUID,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolVersionResponse:
    try:
        version = await protocol_service.pin_protocol_version(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return ProtocolVersionResponse.model_validate(version)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.delete(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_draft_version(
    protocol_version_id: uuid.UUID,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> Response:
    """Permanently delete only an unpublished draft."""
    try:
        await protocol_service.delete_protocol_draft(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.post(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}/archive",
    response_model=ProtocolVersionResponse,
)
async def archive_published_version(
    protocol_version_id: uuid.UUID,
    request: ArchiveProtocolVersionRequest,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ProtocolVersionResponse:
    """Withdraw a published version while retaining immutable evidence."""
    try:
        version = await protocol_service.archive_protocol_version(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
            reason=request.reason,
        )
        await db.commit()
        return ProtocolVersionResponse.model_validate(version)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.delete(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}/purge",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def purge_archived_version(
    protocol_version_id: uuid.UUID,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> Response:
    """Purge an unused archived mistake and its disposable preview evidence."""
    try:
        await protocol_service.purge_archived_protocol_version(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.post(
    "/projects/{project_id}/revisions/{revision_id}/validations",
    response_model=ValidationRunResponse,
)
async def validate_revision(
    revision_id: uuid.UUID,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ValidationRunResponse:
    try:
        run = await protocol_service.validate_revision(
            db, project=access.project, revision_id=revision_id
        )
        await db.commit()
        return ValidationRunResponse.model_validate(run)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.get(
    "/projects/{project_id}/compliance-scans",
    response_model=list[ComplianceScanResponse],
)
async def get_compliance_scans(
    access: ProjectAccess = get_project_read_dep,
    db: AsyncSession = get_db_dep,
) -> list[ComplianceScanResponse]:
    """List recent project-wide protocol scans for project members."""
    scans = await protocol_service.list_compliance_scans(db, project=access.project)
    return [protocol_service.compliance_scan_response(scan) for scan in scans]


@router.post(
    "/projects/{project_id}/protocol-versions/{protocol_version_id}/compliance-scans",
    response_model=ComplianceScanResponse,
    status_code=status.HTTP_201_CREATED,
)
async def post_compliance_scan(
    protocol_version_id: uuid.UUID,
    preview: bool = False,
    access: ProjectAccess = get_protocol_manager_dep,
    db: AsyncSession = get_db_dep,
) -> ComplianceScanResponse:
    """Scan latest accepted files; preview never changes the pinned protocol."""
    try:
        created = await protocol_service.run_compliance_scan(
            db,
            project=access.project,
            protocol_version_id=protocol_version_id,
            actor_user_id=access.user.user_id,
            trigger="preview" if preview else "manual",
        )
        await db.commit()
        scans = await protocol_service.list_compliance_scans(
            db, project=access.project, limit=20
        )
        scan = next(item for item in scans if item.scan_id == created.scan_id)
        return protocol_service.compliance_scan_response(scan)
    except (LookupError, ValueError) as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.put(
    "/projects/{project_id}/protocol-managers/{user_id}",
    response_model=CapabilityGrantResponse,
)
async def grant_protocol_manager(
    user_id: int,
    access: ProjectAccess = get_project_admin_dep,
    db: AsyncSession = get_db_dep,
) -> CapabilityGrantResponse:
    try:
        grant = await protocol_service.grant_protocol_manager(
            db,
            project=access.project,
            user_id=user_id,
            actor_user_id=access.user.user_id,
        )
        await db.commit()
        return CapabilityGrantResponse(
            project_id=grant.project_id,
            user_id=grant.user_id,
            capability=ProjectCapability(grant.capability).value,
        )
    except ValueError as error:
        await db.rollback()
        raise _domain_http_error(error) from error


@router.delete(
    "/projects/{project_id}/protocol-managers/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_protocol_manager(
    user_id: int,
    access: ProjectAccess = get_project_admin_dep,
    db: AsyncSession = get_db_dep,
) -> Response:
    await protocol_service.revoke_protocol_manager(
        db,
        project=access.project,
        user_id=user_id,
        actor_user_id=access.user.user_id,
    )
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
