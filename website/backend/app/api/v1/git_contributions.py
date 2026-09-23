"""Uploading contributions and deciding on them."""

import uuid
from io import BytesIO
from pathlib import Path
from typing import Any, cast

from fastapi import APIRouter, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1 import git_shared
from app.core.errors import ElanoraError, ErrorCode
from app.dependency.database import get_db_dep
from app.dependency.elan_validation import validate_and_record_elan_files
from app.dependency.project_access import (
    ProjectAccess,
    get_project_admin_dep,
    get_project_read_dep,
    get_project_write_dep,
)
from app.elan.validation import EafValidationError
from app.model.enums import ReviewCaseState
from app.model.pending_upload import PendingUpload
from app.model.project import Project
from app.model.research_topic import (
    ProjectBaselineTier,
    ResearchTopic,
    ResearchTopicTier,
)
from app.model.review import ReviewCase
from app.schema.requests.git import (
    ContributionResearchTopicRequest,
    PendingUploadDeclineRequest,
    PendingUploadMergeRequest,
)
from app.schema.responses.git import (
    BatchFileUploadResponse,
    EafReviewResponse,
    PendingUploadsResponse,
)
from app.service.contribution_inspection import MergeReadinessResponse
from app.service.contribution_intake import (
    ContributionAlreadyCurrentError,
    DuplicatePendingContributionError,
)
from app.service.eaf_review import (
    EafReviewUnavailableError,
    compare_repository_eaf,
    comparison_payload,
)
from app.service.research_topics import (
    SimilarResearchTopicError,
    require_distinct_topic_name,
)
from app.service.tier_export import (
    PROVENANCE_PROPERTY,
    ProtectedContextModifiedError,
    TierReintegrationConflictError,
    reintegrate_tier_subset,
    research_extract_metadata,
)
from app.service.upload_naming_compliance import FilenameNotCompliantError

router = APIRouter()


def _string_list(value: object) -> list[str]:
    """Return only string members from untrusted persisted JSON arrays."""
    return (
        [item for item in value if isinstance(item, str)]
        if isinstance(value, list)
        else []
    )


async def _prepare_tier_scoped_uploads(
    files: list[UploadFile],
    project: Project,
    db: AsyncSession,
    *,
    declared_topic_id: int | None,
    proposed_topic_name: str | None,
    contribution_summary: str | None,
) -> tuple[list[UploadFile], dict[str, object]]:
    """Expand research extracts into safe full-file tier-scoped candidates."""
    prepared: list[UploadFile] = []
    scoped_files: list[dict[str, object]] = []
    project_files = Path(project.project_path) / "elan_files"
    marker = PROVENANCE_PROPERTY.encode()
    for upload in files:
        content = await upload.read()
        await upload.seek(0)
        if marker not in content:
            prepared.append(upload)
            continue

        metadata = research_extract_metadata(content)
        if metadata is None:
            prepared.append(upload)
            continue
        source_filename = metadata.get("source_filename")
        if (
            not isinstance(source_filename, str)
            or Path(source_filename).name != source_filename
            or not source_filename.lower().endswith(".eaf")
        ):
            raise ElanoraError(ErrorCode.RESEARCH_COPY_FILENAME_INVALID)
        source = project_files / source_filename
        if not source.is_file():
            raise ElanoraError(
                ErrorCode.RESEARCH_COPY_SOURCE_MISSING, filename=source_filename
            )
        merged = reintegrate_tier_subset(source.read_bytes(), content)
        selected_tiers = metadata.get("selected_tiers", [])
        scoped_files.append(
            {
                "filename": source_filename,
                "topic_id": metadata.get("research_topic_id"),
                "topic_name": metadata.get("research_topic"),
                "selected_tiers": selected_tiers,
                "automatically_included_tiers": metadata.get(
                    "included_parent_tiers", []
                ),
                "baseline_context_tiers": metadata.get("context_tiers", []),
                "editable_baseline_tiers": metadata.get("editable_baseline_tiers", []),
            }
        )
        upload.filename = source_filename
        upload.file = BytesIO(merged)
        upload.size = len(merged)
        prepared.append(upload)

    topic = None
    topic_match = "selected_existing" if declared_topic_id is not None else None
    if declared_topic_id is not None:
        topic = await db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.topic_id == declared_topic_id,
                ResearchTopic.project_id == project.project_id,
            )
        )
        if topic is None:
            raise ElanoraError(ErrorCode.RESEARCH_TOPIC_UNKNOWN)
    embedded_topic_ids = {
        item["topic_id"]
        for item in scoped_files
        if isinstance(item.get("topic_id"), int)
    }
    if declared_topic_id is not None and embedded_topic_ids - {declared_topic_id}:
        raise ElanoraError(ErrorCode.RESEARCH_TOPIC_MISMATCH)
    if topic is None and len(embedded_topic_ids) == 1:
        embedded_topic_id = next(iter(embedded_topic_ids))
        topic = await db.scalar(
            select(ResearchTopic).where(
                ResearchTopic.topic_id == embedded_topic_id,
                ResearchTopic.project_id == project.project_id,
            )
        )
    if len(embedded_topic_ids) > 1:
        raise ElanoraError(ErrorCode.RESEARCH_TOPICS_MIXED)

    proposed_name = (proposed_topic_name or "").strip()
    if topic is None and not scoped_files and proposed_name:
        project_topics = list(
            (
                await db.scalars(
                    select(ResearchTopic).where(
                        ResearchTopic.project_id == project.project_id
                    )
                )
            ).all()
        )
        try:
            require_distinct_topic_name(proposed_name, cast("list[Any]", project_topics))
        except SimilarResearchTopicError as exc:
            suggested = exc.topic
            raise ElanoraError(
                ErrorCode.RESEARCH_TOPIC_SIMILAR,
                suggested_topic_id=getattr(suggested, "topic_id", None),
                suggested_topic_name=suggested.name,
            ) from exc

    topic_tiers = []
    if topic is not None:
        topic_tiers = list(
            (
                await db.scalars(
                    select(ResearchTopicTier.tier_name).where(
                        ResearchTopicTier.topic_id == topic.topic_id
                    )
                )
            ).all()
        )
    baseline_tiers = list(
        (
            await db.scalars(
                select(ProjectBaselineTier.tier_name).where(
                    ProjectBaselineTier.project_id == project.project_id
                )
            )
        ).all()
    )
    scoped_tiers_set: set[str] = set()
    for item in scoped_files:
        selected_tiers = item.get("selected_tiers")
        if isinstance(selected_tiers, list):
            scoped_tiers_set.update(
                tier for tier in selected_tiers if isinstance(tier, str)
            )
    scoped_tiers = sorted(scoped_tiers_set)
    editable_baseline_tiers = sorted(
        {
            tier
            for item in scoped_files
            for tier in _string_list(item.get("editable_baseline_tiers"))
        }
    )
    subject = topic.name if topic else None
    if subject is None and scoped_files:
        embedded_names = {
            str(item["topic_name"]) for item in scoped_files if item.get("topic_name")
        }
        subject = next(iter(embedded_names)) if len(embedded_names) == 1 else None
    return prepared, {
        "summary": (contribution_summary or "").strip(),
        "declared_topic_id": topic.topic_id if topic else None,
        "declared_topic_name": subject,
        "declared_tiers": sorted(set(topic_tiers)) or scoped_tiers,
        "baseline_tiers": sorted(set(baseline_tiers)),
        "declared_baseline_correction_tiers": editable_baseline_tiers,
        "source": "research_copy" if scoped_files else "researcher_declaration",
        "topic_match": topic_match,
        "proposed_topic_name": proposed_name if topic is None else None,
        "topic_review_status": (
            "proposed" if proposed_name and topic is None else "verified"
        ),
        "scoped_files": scoped_files,
    }


@router.post(
    "/projects/{project_id}/upload",
    response_model=BatchFileUploadResponse,
    dependencies=[get_project_write_dep, git_shared.project_lock_dep],
)
async def upload_elan_files(  # noqa: PLR0913, PLR0917
    project_id: int,
    user_name: str = Form(...),
    correction_case_id: uuid.UUID | None = git_shared.correction_case_id_dep,
    research_topic_id: int | None = Form(default=None),
    proposed_topic_name: str | None = Form(default=None, max_length=100),
    contribution_summary: str = Form(min_length=3, max_length=1000),
    files: list[UploadFile] = git_shared.eaf_upload_files_dep,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_write_dep,
) -> BatchFileUploadResponse:
    """Upload an ELAN file to a project.

    Args:
        project_id: Name of the project to upload file to.
        file: ELAN file (.eaf) to upload. File is validated for format and size.
        user_name: Name of the user uploading the file.

    Returns:
        FileUploadResponse: Details of the uploaded file including filename and timestamp.

    Raises:
        ElanoraError: 404 if the project is absent, 422 if EAF validation
            fails, or 500 if upload processing fails.

    Note:
        File validation includes checking for .eaf extension, file size limits,
        valid ELAN XML structure, and filename compliance with the project's naming standard.

    """
    try:
        project = await db.get(Project, project_id)
        if project is None:
            raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)
        allow_current_tree = False
        if correction_case_id is not None:
            review_case = await db.get(ReviewCase, correction_case_id)
            if review_case is None or review_case.project_id != project_id:
                raise ElanoraError(ErrorCode.CORRECTION_REQUEST_NOT_FOUND)
            original_upload = (
                await db.get(PendingUpload, review_case.upload_id)
                if review_case.upload_id is not None
                else None
            )
            if (
                ReviewCaseState(review_case.state) != ReviewCaseState.CHANGES_REQUESTED
                or original_upload is None
                or original_upload.submitted_by != access.user.user_id
            ):
                raise ElanoraError(ErrorCode.CORRECTION_REQUEST_CLOSED)
            allow_current_tree = True
        files, research_context = await _prepare_tier_scoped_uploads(
            files,
            project,
            db,
            declared_topic_id=research_topic_id,
            proposed_topic_name=proposed_topic_name,
            contribution_summary=contribution_summary,
        )
        validated_batch = await validate_and_record_elan_files(
            files,
            db=db,
            instance_id=access.user.instance_id,
            project_id=project_id,
            requested_project_name=project.project_name,
            submitted_by=access.user.user_id,
        )
        result = await git_shared.git_service.add_elan_files(
            project_id,
            validated_batch.files,
            db,
            access.user.user_id,
            user_name,
            protocol_validation={
                "outcome": validated_batch.protocol_outcome,
                "protocol_version_id": (
                    str(validated_batch.protocol_version_id)
                    if validated_batch.protocol_version_id
                    else None
                ),
                "rules_sha256": validated_batch.protocol_rules_sha256,
                "warnings": validated_batch.protocol_warnings,
            },
            research_context=research_context,
            allow_current_tree=allow_current_tree,
        )
        return BatchFileUploadResponse(**result)
    except ProtectedContextModifiedError as e:
        raise ElanoraError(
            ErrorCode.PROTECTED_BASELINE_MODIFIED,
            filename=e.filename,
            tiers=list(e.tiers),
        ) from e
    except TierReintegrationConflictError as e:
        raise ElanoraError(
            ErrorCode.TIER_REINTEGRATION_CONFLICT,
            filename=e.filename,
            tiers=list(e.tiers),
        ) from e
    except FilenameNotCompliantError as e:
        raise ElanoraError(
            ErrorCode.FILENAME_NOT_COMPLIANT,
            filename=e.filename,
            pattern=e.pattern,
        ) from e
    except (HTTPException, ElanoraError):
        raise
    except ContributionAlreadyCurrentError as e:
        raise ElanoraError(ErrorCode.CONTRIBUTION_NO_CHANGES) from e
    except DuplicatePendingContributionError as e:
        raise ElanoraError(
            ErrorCode.CONTRIBUTION_DUPLICATE_PENDING, upload_id=e.upload_id
        ) from e
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_FILE_NOT_FOUND) from e
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_OPERATION_INVALID) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get(
    "/projects/{project_name}/admin/pending-uploads",
    response_model=PendingUploadsResponse,
    dependencies=[get_project_read_dep],
)
async def get_pending_uploads(
    project_name: str,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_read_dep,
) -> PendingUploadsResponse:
    """List contribution status for authorized project members."""
    try:
        result = await git_shared.git_service.get_pending_uploads_with_status(
            project_name, db
        )
        return PendingUploadsResponse(**cast("dict[str, Any]", result))
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_FILE_NOT_FOUND) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/test",
    dependencies=[get_project_admin_dep],
)
async def test_pending_upload(
    project_name: str,
    branch_name: str,
    access: ProjectAccess = get_project_admin_dep,
) -> MergeReadinessResponse:
    """Test whether a pending contribution merges cleanly without changing history."""
    try:
        return git_shared.git_service.test_pending_upload(project_name, branch_name)
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.get(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/eaf-review",
    response_model=EafReviewResponse,
    dependencies=[get_project_read_dep],
)
async def review_pending_eaf(
    project_name: str,
    branch_name: str,
    filename: str,
    access: ProjectAccess = get_project_read_dep,
) -> EafReviewResponse:
    """Return a read-only semantic comparison without mutating project state."""
    try:
        comparison = compare_repository_eaf(
            git_shared.git_service.base_path, project_name, branch_name, filename
        )
        return EafReviewResponse(**cast("dict[str, Any]", comparison_payload(comparison)))
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc
    except (EafReviewUnavailableError, EafValidationError) as exc:
        raise ElanoraError(ErrorCode.EAF_REVIEW_UNAVAILABLE) from exc


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{branch_name}/merge",
    dependencies=[get_project_admin_dep, git_shared.project_lock_dep],
)
async def merge_pending_upload(
    project_name: str,
    branch_name: str,
    request: PendingUploadMergeRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Durably request and execute publication of one reviewed contribution."""
    try:
        change_set = await git_shared.contribution_change_sets.request(
            db,
            project_name=project_name,
            branch_name=branch_name,
            resolution_strategy=request.resolution_strategy,
            requested_by=access.user.user_id,
        )
        return await git_shared.contribution_change_sets.execute(
            db, change_set.change_set_id
        )
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.post(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/decline",
    dependencies=[get_project_admin_dep, git_shared.project_lock_dep],
)
async def decline_pending_upload(
    project_name: str,
    upload_id: int,
    request: PendingUploadDeclineRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Decline a contribution while retaining its provenance and review history."""
    try:
        return await git_shared.git_service.decline_pending_upload(
            project_name, upload_id, request.reason, db, access.user.user_id
        )
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e


@router.put(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/research-topic",
    dependencies=[get_project_admin_dep],
)
async def set_contribution_research_topic(
    project_name: str,
    upload_id: int,
    request: ContributionResearchTopicRequest,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Assign or create the curated topic used to classify a contribution."""
    try:
        return await git_shared.git_service.set_contribution_research_topic(
            project_name,
            upload_id,
            request.topic_id,
            request.new_topic_name,
            db,
        )
    except FileNotFoundError as exc:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from exc
    except ValueError as exc:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from exc


@router.delete(
    "/projects/{project_name}/admin/pending-uploads/{upload_id}/duplicate",
    dependencies=[get_project_admin_dep, git_shared.project_lock_dep],
)
async def dismiss_duplicate_upload(
    project_name: str,
    upload_id: int,
    db: AsyncSession = get_db_dep,
    access: ProjectAccess = get_project_admin_dep,
) -> dict[str, Any]:
    """Remove a redundant pending branch while retaining provenance and audit history."""
    try:
        return await git_shared.git_service.dismiss_duplicate_upload(
            project_name, upload_id, db, access.user.user_id
        )
    except ElanoraError:
        raise
    except FileNotFoundError as e:
        raise ElanoraError(ErrorCode.PROJECT_RESOURCE_NOT_FOUND) from e
    except ValueError as e:
        raise ElanoraError(ErrorCode.PROJECT_STATE_CONFLICT) from e
    except Exception as e:
        raise ElanoraError(ErrorCode.INTERNAL_ERROR) from e
