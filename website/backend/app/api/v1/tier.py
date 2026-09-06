from pathlib import Path

from fastapi import APIRouter, HTTPException, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependency.database import get_db_dep
from app.dependency.project_access import ProjectAccess, get_project_read_dep
from app.dependency.user import get_admin_dep
from app.schema.requests.tier import (
    CreateSectionRequest,
    DeleteSectionRequest,
    MoveTierGroupRequest,
    RenameSectionRequest,
    TierSubsetExportRequest,
)
from app.schema.responses.tier import SectionsAndGroupsResponse, TierTreeResponse
from app.service.git import GitService
from app.service.tier import TierGroupService, TierSectionService, TierService
from app.service.tier_export import build_tier_subset
from app.storage.paths import safe_project_path

router = APIRouter()


@router.post("/{project_name}/export")
async def export_tier_subset(
    project_name: str,
    request: TierSubsetExportRequest,
    access: ProjectAccess = get_project_read_dep,
):
    """Download a derived EAF containing only selected tiers and dependencies."""
    filename = Path(request.filename)
    if filename.name != request.filename or filename.suffix.lower() != ".eaf":
        raise HTTPException(status_code=400, detail="Select a valid EAF filename.")

    project_path = safe_project_path(GitService().base_path, project_name)
    source = project_path / "elan_files" / filename.name
    try:
        source.resolve().relative_to((project_path / "elan_files").resolve())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid EAF filename.") from exc
    if not source.is_file():
        raise HTTPException(status_code=404, detail="The selected EAF file was not found.")

    try:
        export = build_tier_subset(
            source.read_bytes(), request.tier_names, filename.name
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    download_name = filename.name
    return Response(
        content=export.content,
        media_type="application/xml",
        headers={
            "Content-Disposition": f'attachment; filename="{download_name}"',
            "X-Elanora-Included-Tiers": str(len(export.included_tiers)),
            "X-Elanora-Automatic-Parents": str(
                len(export.automatically_included_tiers)
            ),
        },
    )


@router.get("/{project_name}", response_model=TierTreeResponse)
async def get_tiers(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
):
    """Get all tiers for a project, grouped by ELAN file.

    Returns a list of tier trees (one per file).
    """
    result = await TierService.get_project_tiers_grouped_by_file(db, project_name)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Project not found or no tiers available."
        )

    # Unwrap the 'tiers' key if present
    tiers_dict = result.get("tiers", result)

    # Now serialize
    serialized = {k: [n.model_dump() for n in v] for k, v in tiers_dict.items()}
    return {"tiers": serialized}


@router.get("/{project_id}/sections", response_model=SectionsAndGroupsResponse)
async def get_sections_and_groups(
    project_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
):
    return await TierSectionService.get_sections_and_groups(db, project_id)


@router.post("/sections/create")
async def create_section(
    request: CreateSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    return await TierSectionService.create_section(db, request.project_id, request.name)


@router.post("/sections/rename")
async def rename_section(
    request: RenameSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    return await TierSectionService.rename_section(
        db, request.section_id, request.new_name
    )


@router.post("/sections/delete")
async def delete_section(
    request: DeleteSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    return await TierSectionService.delete_section(db, request.section_id)


@router.post("/tier_group/move")
async def move_tier_group(
    request: MoveTierGroupRequest,
    db: AsyncSession = get_db_dep,
    admin_user=get_admin_dep,
):
    return await TierGroupService.assign_group_to_section(
        db, request.tier_group_id, request.section_id
    )
