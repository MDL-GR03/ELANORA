from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
)
from app.dependency.user import get_admin_dep
from app.model.research_topic import (
    ProjectBaselineTier,
    ResearchTopic,
    ResearchTopicTier,
)
from app.model.user import User
from app.schema.requests.tier import (
    CreateSectionRequest,
    DeleteSectionRequest,
    MoveTierGroupRequest,
    ProjectBaselineTiersRequest,
    RenameSectionRequest,
    ResearchTopicRequest,
    TierSubsetExportRequest,
)
from app.schema.responses.tier import (
    ProjectBaselineTiersInfo,
    ResearchTopicInfo,
    SectionInfo,
    SectionsAndGroupsResponse,
    TierTreeResponse,
)
from app.service.git import GitService
from app.service.research_topics import (
    SimilarResearchTopicError,
    require_distinct_topic_name,
)
from app.service.tier import TierGroupService, TierSectionService, TierService
from app.service.tier_export import build_tier_subset
from app.storage.paths import safe_project_path

router = APIRouter()


@router.post("/{project_name}/export")
async def export_tier_subset(
    project_name: str,
    request: TierSubsetExportRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> Response:
    """Download a derived EAF containing only selected tiers and dependencies."""
    filename = Path(request.filename)
    if filename.name != request.filename or filename.suffix.lower() != ".eaf":
        raise ElanoraError(ErrorCode.EAF_FILENAME_INVALID)

    project_path = safe_project_path(GitService().base_path, project_name)
    source = project_path / "elan_files" / filename.name
    try:
        source.resolve().relative_to((project_path / "elan_files").resolve())
    except ValueError as exc:
        raise ElanoraError(ErrorCode.EAF_FILENAME_INVALID) from exc
    if not source.is_file():
        raise ElanoraError(ErrorCode.EAF_FILE_NOT_FOUND)

    topic = None
    if request.topic_id is not None:
        topic = await db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.topic_id == request.topic_id,
                ResearchTopic.project_id == access.project.project_id,
            )
        )
        if topic is None:
            raise ElanoraError(ErrorCode.RESEARCH_TOPIC_NOT_FOUND)
    try:
        baseline_tiers = list(
            (
                await db.scalars(
                    select(ProjectBaselineTier.tier_name).where(
                        ProjectBaselineTier.project_id == access.project.project_id
                    )
                )
            ).all()
        )
        baseline_set = set(baseline_tiers)
        requested_context = (
            baseline_set
            if request.context_tier_names is None
            else set(request.context_tier_names)
        )
        editable_baseline = set(request.editable_baseline_tier_names)
        unknown_baseline = sorted(
            (requested_context | editable_baseline) - baseline_set
        )
        if unknown_baseline:
            raise ValueError(
                f"Not configured as project baseline tier(s): {', '.join(unknown_baseline)}"
            )
        export = build_tier_subset(
            source.read_bytes(),
            request.tier_names,
            filename.name,
            topic_id=topic.topic_id if topic else None,
            topic_name=topic.name if topic else None,
            context_tier_names=sorted(requested_context | editable_baseline),
            editable_baseline_tier_names=sorted(editable_baseline),
            allowed_new_tier_names=(
                [item.tier_name for item in topic.tiers]
                if topic and topic.allow_new_tiers
                else None
            ),
        )
    except ValueError as exc:
        raise ElanoraError(ErrorCode.RESEARCH_COPY_SELECTION_INVALID) from exc

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


def _topic_response(topic: ResearchTopic) -> ResearchTopicInfo:
    return ResearchTopicInfo(
        topic_id=topic.topic_id,
        name=topic.name,
        description=topic.description,
        allow_new_tiers=topic.allow_new_tiers,
        tier_names=sorted(item.tier_name for item in topic.tiers),
    )


@router.get("/{project_id}/baseline-tiers", response_model=ProjectBaselineTiersInfo)
async def get_project_baseline_tiers(
    project_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> ProjectBaselineTiersInfo:
    names = (
        await db.scalars(
            select(ProjectBaselineTier.tier_name)
            .where(ProjectBaselineTier.project_id == project_id)
            .order_by(ProjectBaselineTier.tier_name)
        )
    ).all()
    return ProjectBaselineTiersInfo(tier_names=list(names))


@router.put("/{project_id}/baseline-tiers", response_model=ProjectBaselineTiersInfo)
async def update_project_baseline_tiers(
    project_id: int,
    request: ProjectBaselineTiersRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ProjectBaselineTiersInfo:
    existing = list(
        (
            await db.scalars(
                select(ProjectBaselineTier).where(
                    ProjectBaselineTier.project_id == project_id
                )
            )
        ).all()
    )
    for item in existing:
        await db.delete(item)
    names = sorted({name.strip() for name in request.tier_names if name.strip()})
    db.add_all(
        [ProjectBaselineTier(project_id=project_id, tier_name=name) for name in names]
    )
    await db.commit()
    return ProjectBaselineTiersInfo(tier_names=names)


@router.get("/{project_id}/topics", response_model=list[ResearchTopicInfo])
async def get_research_topics(
    project_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> list[ResearchTopicInfo]:
    topics = (
        await db.scalars(
            select(ResearchTopic)
            .where(ResearchTopic.project_id == project_id)
            .order_by(ResearchTopic.name)
        )
    ).all()
    return [_topic_response(topic) for topic in topics]


@router.post("/{project_id}/topics", response_model=ResearchTopicInfo, status_code=201)
async def create_research_topic(
    project_id: int,
    request: ResearchTopicRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ResearchTopicInfo:
    existing_topics = list(
        (
            await db.scalars(
                select(ResearchTopic).where(ResearchTopic.project_id == project_id)
            )
        ).all()
    )
    try:
        require_distinct_topic_name(request.name, cast("list[Any]", existing_topics))
    except SimilarResearchTopicError as exc:
        raise ElanoraError(
            ErrorCode.RESEARCH_TOPIC_USE_EXISTING, name=exc.topic.name
        ) from exc
    topic = ResearchTopic(
        project_id=project_id,
        name=request.name.strip(),
        description=(request.description or "").strip() or None,
        allow_new_tiers=request.allow_new_tiers,
        tiers=[
            ResearchTopicTier(tier_name=name)
            for name in sorted(set(request.tier_names))
        ],
    )
    db.add(topic)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ElanoraError(ErrorCode.RESEARCH_TOPIC_EXISTS) from exc
    await db.refresh(topic, attribute_names=["tiers"])
    return _topic_response(topic)


@router.put("/{project_id}/topics/{topic_id}", response_model=ResearchTopicInfo)
async def update_research_topic(
    project_id: int,
    topic_id: int,
    request: ResearchTopicRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> ResearchTopicInfo:
    topic = await db.scalar(
        select(ResearchTopic).where(
            ResearchTopic.topic_id == topic_id,
            ResearchTopic.project_id == project_id,
        )
    )
    if topic is None:
        raise ElanoraError(ErrorCode.RESEARCH_TOPIC_NOT_FOUND)
    other_topics = list(
        (
            await db.scalars(
                select(ResearchTopic).where(
                    ResearchTopic.project_id == project_id,
                    ResearchTopic.topic_id != topic_id,
                )
            )
        ).all()
    )
    try:
        require_distinct_topic_name(request.name, cast("list[Any]", other_topics))
    except SimilarResearchTopicError as exc:
        raise ElanoraError(
            ErrorCode.RESEARCH_TOPIC_USE_EXISTING, name=exc.topic.name
        ) from exc
    topic.name = request.name.strip()
    topic.description = (request.description or "").strip() or None
    topic.allow_new_tiers = request.allow_new_tiers
    topic.tiers = [
        ResearchTopicTier(tier_name=name) for name in sorted(set(request.tier_names))
    ]
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise ElanoraError(ErrorCode.RESEARCH_TOPIC_EXISTS) from exc
    await db.refresh(topic, attribute_names=["tiers"])
    return _topic_response(topic)


@router.delete("/{project_id}/topics/{topic_id}", status_code=204)
async def delete_research_topic(
    project_id: int,
    topic_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> Response:
    topic = await db.scalar(
        select(ResearchTopic).where(
            ResearchTopic.topic_id == topic_id,
            ResearchTopic.project_id == project_id,
        )
    )
    if topic is None:
        raise ElanoraError(ErrorCode.RESEARCH_TOPIC_NOT_FOUND)
    await db.delete(topic)
    await db.commit()
    return Response(status_code=204)


@router.get("/{project_name}", response_model=TierTreeResponse)
async def get_tiers(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> TierTreeResponse:
    """Get all tiers for a project, grouped by ELAN file.

    Returns a list of tier trees (one per file).
    """
    result = await TierService.get_project_tiers_grouped_by_file(db, project_name)
    if result is None:
        raise ElanoraError(ErrorCode.TIERS_NOT_FOUND)

    # Unwrap the 'tiers' key if present
    tiers_dict = result.get("tiers", {})

    # Now serialize
    serialized = {k: [n.model_dump() for n in v] for k, v in tiers_dict.items()}
    return TierTreeResponse(tiers=cast("dict[str, Any]", serialized))


@router.get("/{project_id}/sections", response_model=SectionsAndGroupsResponse)
async def get_sections_and_groups(
    project_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> SectionsAndGroupsResponse:
    return await TierSectionService.get_sections_and_groups(db, project_id)


@router.post("/sections/create", response_model=SectionInfo)
async def create_section(
    request: CreateSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user: User = get_admin_dep,
) -> SectionInfo:
    section = await TierSectionService.create_section(
        db, request.project_id, request.name
    )
    return SectionInfo(
        section_id=section.tier_section_id,
        name=section.section_name,
    )


@router.post("/sections/rename")
async def rename_section(
    request: RenameSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user: User = get_admin_dep,
) -> int:
    return await TierSectionService.rename_section(
        db, request.section_id, request.new_name
    )


@router.post("/sections/delete")
async def delete_section(
    request: DeleteSectionRequest,
    db: AsyncSession = get_db_dep,
    admin_user: User = get_admin_dep,
) -> int:
    return await TierSectionService.delete_section(db, request.section_id)


@router.post("/tier_group/move")
async def move_tier_group(
    request: MoveTierGroupRequest,
    db: AsyncSession = get_db_dep,
    admin_user: User = get_admin_dep,
) -> int:
    return await TierGroupService.assign_group_to_section(
        db, request.tier_group_id, request.section_id
    )
