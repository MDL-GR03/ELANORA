"""Use cases for immutable protocols and revision validation evidence."""

import asyncio
import hashlib
import json
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from lxml import etree
from sqlalchemy import delete, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.elan.validation import SCHEMA_PATH, EafValidationError, validate_eaf
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.audit_event import AuditEvent
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import (
    ProjectCapability,
    ProtocolVersionStatus,
    ValidationOutcome,
    ValidationSeverity,
)
from app.model.project import Project
from app.model.protocol import (
    ProjectComplianceScan,
    ProjectComplianceScanFile,
    Protocol,
    ProtocolValidationIssue,
    ProtocolVersion,
    ProtocolVersionArchive,
    ValidationRun,
    ValidatorRelease,
)
from app.model.review import ReviewCase
from app.schema.protocol import (
    ComplianceScanFileResponse,
    ComplianceScanResponse,
    CorpusProtocolSuggestionResponse,
    ProtocolRules,
    ProtocolTierSuggestion,
    ProtocolVocabularySuggestion,
    ValidationIssueResponse,
)

VALIDATOR_NAME = "elanora-eaf"
VALIDATOR_VERSION = "1"
FULL_COVERAGE_PERCENT = 100.0


class ProtocolConflictError(ValueError):
    """Raised when a requested protocol lifecycle transition is invalid."""


class ProtocolNotFoundError(LookupError):
    """Raised when protocol state is outside the authorized project scope."""


@dataclass(frozen=True, slots=True)
class ProtocolFinding:
    """One deterministic researcher-facing finding from a protocol snapshot."""

    code: str
    severity: ValidationSeverity
    location: str
    message: str
    rule_key: str


def evaluate_protocol_rules(
    root: etree._Element, rules: ProtocolRules
) -> tuple[ProtocolFinding, ...]:
    """Evaluate a validated EAF document against immutable protocol rules."""
    findings: list[ProtocolFinding] = []

    def error(code: str, location: str, message: str, rule_key: str) -> None:
        findings.append(
            ProtocolFinding(
                code=code,
                severity=ValidationSeverity.ERROR,
                location=location,
                message=message,
                rule_key=rule_key,
            )
        )

    tiers = {
        tier_id: tier
        for tier in root.findall("TIER")
        if (tier_id := tier.get("TIER_ID")) is not None
    }
    tier_ids = set(tiers)
    for tier_id in rules.required_tiers:
        if tier_id not in tier_ids:
            error(
                "protocol.required_tier_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required tier {tier_id!r} is missing",
                "required_tiers",
            )
    for tier_id, required_parent in rules.tier_parents.items():
        tier = tiers.get(tier_id)
        if tier is not None and tier.get("PARENT_REF") != required_parent:
            error(
                "protocol.tier_parent_mismatch",
                f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']",
                f"Tier {tier_id!r} must have parent {required_parent!r}",
                "tier_parents",
            )
    for tier_id, required_type in rules.tier_linguistic_types.items():
        tier = tiers.get(tier_id)
        if tier is not None and tier.get("LINGUISTIC_TYPE_REF") != required_type:
            error(
                "protocol.tier_linguistic_type_mismatch",
                f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']",
                f"Tier {tier_id!r} must use linguistic type {required_type!r}",
                "tier_linguistic_types",
            )
    vocabulary_ids = {
        item.get("CV_ID")
        for item in root.findall("CONTROLLED_VOCABULARY")
        if item.get("CV_ID")
    }
    for vocabulary_id in rules.required_controlled_vocabularies:
        if vocabulary_id not in vocabulary_ids:
            error(
                "protocol.required_vocabulary_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required controlled vocabulary {vocabulary_id!r} is missing",
                "required_controlled_vocabularies",
            )
    media = root.findall("HEADER/MEDIA_DESCRIPTOR")
    if rules.media_required and not media:
        error(
            "protocol.media_required",
            "/ANNOTATION_DOCUMENT/HEADER",
            "At least one media descriptor is required",
            "media_required",
        )
    allowed_mime_types = set(rules.allowed_media_mime_types)
    if allowed_mime_types:
        for descriptor in media:
            mime_type = descriptor.get("MIME_TYPE", "")
            if mime_type not in allowed_mime_types:
                error(
                    "protocol.media_mime_type_forbidden",
                    root.getroottree().getpath(descriptor),
                    f"Media MIME type {mime_type!r} is not permitted",
                    "allowed_media_mime_types",
                )
    return tuple(findings)


async def get_pinned_protocol_version(
    db: AsyncSession, project: Project
) -> ProtocolVersion | None:
    """Resolve the project's published immutable protocol snapshot, if configured."""
    if project.protocol_version_id is None:
        return None
    version = await db.scalar(
        select(ProtocolVersion).where(
            ProtocolVersion.protocol_version_id == project.protocol_version_id,
            ProtocolVersion.status == ProtocolVersionStatus.PUBLISHED,
        )
    )
    if version is None:
        raise ProtocolConflictError(
            "The project's pinned protocol is unavailable or unpublished"
        )
    return version


def validate_content_against_protocol(
    content: bytes, version: ProtocolVersion
) -> tuple[ProtocolFinding, ...]:
    """Validate EAF structure and apply one published protocol snapshot."""
    root = validate_eaf(content)
    return evaluate_protocol_rules(root, ProtocolRules.model_validate(version.rules))


def _rules_dict(rules: ProtocolRules) -> dict[str, object]:
    return rules.model_dump(mode="json")


def _rules_checksum(rules: dict[str, object]) -> str:
    canonical = json.dumps(
        rules, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


async def suggest_protocol_from_corpus(
    db: AsyncSession, project: Project
) -> CorpusProtocolSuggestionResponse:
    """Infer conservative, evidence-backed rules from latest accepted revisions."""
    latest_number = (
        select(
            EafRevision.elan_id,
            func.max(EafRevision.revision_number).label("revision_number"),
        )
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project.project_id)
        .group_by(EafRevision.elan_id)
        .subquery()
    )
    revisions = list(
        (
            await db.scalars(
                select(EafRevision)
                .join(
                    latest_number,
                    (latest_number.c.elan_id == EafRevision.elan_id)
                    & (latest_number.c.revision_number == EafRevision.revision_number),
                )
                .options(selectinload(EafRevision.elan_file))
                .order_by(EafRevision.elan_id)
            )
        ).all()
    )
    tier_counts: Counter[str] = Counter()
    tier_parents: dict[str, Counter[str]] = defaultdict(Counter)
    tier_types: dict[str, Counter[str]] = defaultdict(Counter)
    vocabulary_counts: Counter[str] = Counter()
    media_type_counts: Counter[str] = Counter()
    files_with_media = 0
    skipped_files: list[str] = []
    analyzed_files = 0

    for revision in revisions:
        try:
            root = await asyncio.to_thread(validate_eaf, revision.raw_xml)
        except EafValidationError:
            skipped_files.append(revision.elan_file.filename)
            continue
        analyzed_files += 1
        file_tiers: set[str] = set()
        for tier in root.findall("TIER"):
            tier_id = tier.get("TIER_ID")
            if not tier_id or tier_id in file_tiers:
                continue
            file_tiers.add(tier_id)
            if parent := tier.get("PARENT_REF"):
                tier_parents[tier_id][parent] += 1
            if linguistic_type := tier.get("LINGUISTIC_TYPE_REF"):
                tier_types[tier_id][linguistic_type] += 1
        tier_counts.update(file_tiers)
        vocabulary_counts.update(
            {
                vocabulary_id
                for vocabulary in root.findall("CONTROLLED_VOCABULARY")
                if (vocabulary_id := vocabulary.get("CV_ID"))
            }
        )
        descriptors = root.findall("HEADER/MEDIA_DESCRIPTOR")
        if descriptors:
            files_with_media += 1
        media_type_counts.update(
            {
                mime_type
                for descriptor in descriptors
                if (mime_type := descriptor.get("MIME_TYPE"))
            }
        )

    def consensus(
        variants: Counter[str], occurrences: int
    ) -> tuple[str | None, float | None]:
        if not variants or not occurrences:
            return None, None
        value, count = variants.most_common(1)[0]
        return value, round(count * 100 / occurrences, 1)

    tier_suggestions: list[ProtocolTierSuggestion] = []
    for tier_id, count in tier_counts.most_common():
        parent, parent_consistency = consensus(tier_parents[tier_id], count)
        linguistic_type, type_consistency = consensus(tier_types[tier_id], count)
        tier_suggestions.append(
            ProtocolTierSuggestion(
                tier_id=tier_id,
                occurrence_count=count,
                coverage_percent=round(count * 100 / analyzed_files, 1),
                suggested_required=count == analyzed_files,
                parent_ref=parent,
                parent_consistency_percent=parent_consistency,
                parent_variants=dict(tier_parents[tier_id]),
                linguistic_type_ref=linguistic_type,
                linguistic_type_consistency_percent=type_consistency,
                linguistic_type_variants=dict(tier_types[tier_id]),
            )
        )
    vocabulary_suggestions = (
        [
            ProtocolVocabularySuggestion(
                vocabulary_id=vocabulary_id,
                occurrence_count=count,
                coverage_percent=round(count * 100 / analyzed_files, 1),
                suggested_required=count == analyzed_files,
            )
            for vocabulary_id, count in vocabulary_counts.most_common()
        ]
        if analyzed_files
        else []
    )
    required_tiers = [
        item.tier_id for item in tier_suggestions if item.suggested_required
    ]
    required_set = set(required_tiers)
    proposed_rules = ProtocolRules(
        required_tiers=required_tiers,
        tier_parents={
            item.tier_id: item.parent_ref
            for item in tier_suggestions
            if item.suggested_required
            and item.parent_ref in required_set
            and item.parent_consistency_percent == FULL_COVERAGE_PERCENT
        },
        tier_linguistic_types={
            item.tier_id: item.linguistic_type_ref
            for item in tier_suggestions
            if item.suggested_required
            and item.linguistic_type_ref is not None
            and item.linguistic_type_consistency_percent == FULL_COVERAGE_PERCENT
        },
        required_controlled_vocabularies=[
            item.vocabulary_id
            for item in vocabulary_suggestions
            if item.suggested_required
        ],
        media_required=analyzed_files > 0 and files_with_media == analyzed_files,
        allowed_media_mime_types=sorted(media_type_counts),
    )
    return CorpusProtocolSuggestionResponse(
        total_files=len(revisions),
        analyzed_files=analyzed_files,
        skipped_files=skipped_files,
        tier_suggestions=tier_suggestions,
        vocabulary_suggestions=vocabulary_suggestions,
        media_type_counts=dict(media_type_counts),
        files_with_media=files_with_media,
        proposed_rules=proposed_rules,
    )


async def create_protocol(
    db: AsyncSession,
    *,
    project: Project,
    name: str,
    description: str | None,
    rules: ProtocolRules,
    actor_user_id: int,
) -> Protocol:
    """Create an institution protocol and its first mutable draft."""
    protocol = Protocol(
        instance_id=project.instance_id,
        name=name.strip(),
        description=description,
        created_by=actor_user_id,
    )
    protocol.versions.append(
        ProtocolVersion(
            version_number=1,
            status=ProtocolVersionStatus.DRAFT,
            rules=_rules_dict(rules),
            created_by=actor_user_id,
        )
    )
    db.add(protocol)
    await db.flush()
    return protocol


async def list_protocols(db: AsyncSession, project: Project) -> list[Protocol]:
    """List only protocols owned by the project's institution."""
    return list(
        (
            await db.scalars(
                select(Protocol)
                .where(Protocol.instance_id == project.instance_id)
                .options(
                    selectinload(Protocol.versions).selectinload(
                        ProtocolVersion.archive
                    )
                )
                .order_by(Protocol.name)
            )
        ).all()
    )


async def create_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_id: uuid.UUID,
    rules: ProtocolRules,
    actor_user_id: int,
) -> ProtocolVersion:
    """Append the next draft version while serializing version allocation."""
    protocol = await db.scalar(
        select(Protocol)
        .where(
            Protocol.protocol_id == protocol_id,
            Protocol.instance_id == project.instance_id,
        )
        .with_for_update()
    )
    if protocol is None:
        raise ProtocolNotFoundError("Protocol not found")
    next_version = await db.scalar(
        select(func.coalesce(func.max(ProtocolVersion.version_number), 0) + 1).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    version = ProtocolVersion(
        protocol_id=protocol_id,
        version_number=next_version,
        status=ProtocolVersionStatus.DRAFT,
        rules=_rules_dict(rules),
        created_by=actor_user_id,
    )
    db.add(version)
    await db.flush()
    return version


async def update_draft(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    rules: ProtocolRules,
) -> ProtocolVersion:
    """Replace rules only while the selected version remains a draft."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Published protocol versions are immutable")
    version.rules = _rules_dict(rules)
    await db.flush()
    return version


async def publish_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> ProtocolVersion:
    """Freeze a draft and append auditable publication evidence."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Protocol version is already published")
    validated_rules = ProtocolRules.model_validate(version.rules)
    version.rules = _rules_dict(validated_rules)
    version.rules_sha256 = _rules_checksum(version.rules)
    version.status = ProtocolVersionStatus.PUBLISHED
    version.published_by = actor_user_id
    version.published_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.published",
            resource_type="protocol_version",
            resource_id=str(version.protocol_version_id),
            details={"rules_sha256": version.rules_sha256},
        )
    )
    await db.flush()
    return version


async def pin_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> ProtocolVersion:
    """Pin a project to a published protocol owned by its institution."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("A project can only pin a published protocol")
    if version.archive is not None:
        raise ProtocolConflictError("An archived protocol version cannot be activated")
    project.protocol_version_id = version.protocol_version_id
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="project.protocol.pinned",
            resource_type="protocol_version",
            resource_id=str(version.protocol_version_id),
            details={},
        )
    )
    await db.flush()
    return version


async def delete_protocol_draft(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> None:
    """Delete a draft; published research evidence is never deletable."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.DRAFT:
        raise ProtocolConflictError("Published protocol versions cannot be deleted")
    protocol_id = version.protocol_id
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.draft.deleted",
            resource_type="protocol_version",
            resource_id=str(protocol_version_id),
            details={"protocol_id": str(protocol_id)},
        )
    )
    version_count = await db.scalar(
        select(func.count(ProtocolVersion.protocol_version_id)).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    if version_count == 1:
        protocol = await db.get(Protocol, protocol_id)
        if protocol is not None:
            await db.delete(protocol)
    else:
        await db.delete(version)
    await db.flush()


async def archive_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
    reason: str | None,
) -> ProtocolVersion:
    """Withdraw a published version from future use without mutating it."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("Draft versions should be deleted, not archived")
    if version.archive is not None:
        raise ProtocolConflictError("Protocol version is already archived")
    active_project = await db.scalar(
        select(Project.project_id).where(
            Project.protocol_version_id == protocol_version_id,
            Project.deleted_at.is_(None),
        )
    )
    if active_project is not None:
        raise ProtocolConflictError(
            "Replace the active project protocol before archiving this version"
        )
    archive = ProtocolVersionArchive(
        protocol_version_id=protocol_version_id,
        archived_by=actor_user_id,
        reason=reason.strip() if reason else None,
    )
    db.add(archive)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.archived",
            resource_type="protocol_version",
            resource_id=str(protocol_version_id),
            details={"reason": archive.reason},
        )
    )
    await db.flush()
    version.archive = archive
    return version


async def purge_archived_protocol_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
) -> None:
    """Purge an unused mistake plus disposable previews, retaining a tombstone."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id, lock=True
    )
    if version.status != ProtocolVersionStatus.PUBLISHED or version.archive is None:
        raise ProtocolConflictError("Only archived published versions can be purged")
    version_id_text = str(protocol_version_id)
    was_activated = await db.scalar(
        select(AuditEvent.event_id).where(
            AuditEvent.action == "project.protocol.pinned",
            AuditEvent.resource_type == "protocol_version",
            AuditEvent.resource_id == version_id_text,
        )
    )
    if was_activated is not None:
        raise ProtocolConflictError(
            "This version was activated and must remain in the research history"
        )
    if (
        await db.scalar(
            select(Project.project_id).where(
                Project.protocol_version_id == protocol_version_id
            )
        )
        is not None
    ):
        raise ProtocolConflictError("The active project protocol cannot be purged")
    non_preview_scan = await db.scalar(
        select(ProjectComplianceScan.scan_id).where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger != "preview",
        )
    )
    if non_preview_scan is not None:
        raise ProtocolConflictError(
            "This version has a non-preview compliance scan and must be retained"
        )
    preview_run_ids = (
        select(ProjectComplianceScanFile.validation_run_id)
        .join(
            ProjectComplianceScan,
            ProjectComplianceScan.scan_id == ProjectComplianceScanFile.scan_id,
        )
        .where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger == "preview",
        )
    )
    external_run = await db.scalar(
        select(ValidationRun.validation_run_id).where(
            ValidationRun.protocol_version_id == protocol_version_id,
            ValidationRun.validation_run_id.not_in(preview_run_ids),
        )
    )
    if external_run is not None:
        raise ProtocolConflictError(
            "This version validated work outside a preview and must be retained"
        )
    reviewed_issue = await db.scalar(
        select(ReviewCase.case_id)
        .join(
            ProtocolValidationIssue,
            ProtocolValidationIssue.validation_issue_id
            == ReviewCase.validation_issue_id,
        )
        .join(
            ValidationRun,
            ValidationRun.validation_run_id
            == ProtocolValidationIssue.validation_run_id,
        )
        .where(ValidationRun.protocol_version_id == protocol_version_id)
    )
    if reviewed_issue is not None:
        raise ProtocolConflictError(
            "A correction discussion references this version, so it must be retained"
        )

    protocol_id = version.protocol_id
    version_count = await db.scalar(
        select(func.count(ProtocolVersion.protocol_version_id)).where(
            ProtocolVersion.protocol_id == protocol_id
        )
    )
    rules_checksum = version.rules_sha256
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="protocol.version.purged",
            resource_type="protocol_version_tombstone",
            resource_id=version_id_text,
            details={
                "protocol_id": str(protocol_id),
                "version_number": version.version_number,
                "rules_sha256": rules_checksum,
                "archive_reason": version.archive.reason,
            },
        )
    )
    await db.flush()
    await db.execute(
        delete(ProjectComplianceScan).where(
            ProjectComplianceScan.protocol_version_id == protocol_version_id,
            ProjectComplianceScan.trigger == "preview",
        )
    )
    run_ids = select(ValidationRun.validation_run_id).where(
        ValidationRun.protocol_version_id == protocol_version_id
    )
    await db.execute(text("SET LOCAL elanora.allow_protocol_purge = 'on'"))
    await db.execute(
        delete(ProtocolValidationIssue).where(
            ProtocolValidationIssue.validation_run_id.in_(run_ids)
        )
    )
    await db.execute(
        delete(ValidationRun).where(
            ValidationRun.protocol_version_id == protocol_version_id
        )
    )
    if version_count == 1:
        protocol = await db.get(Protocol, protocol_id)
        if protocol is not None:
            await db.delete(protocol)
    else:
        await db.delete(version)
    await db.flush()


async def grant_protocol_manager(
    db: AsyncSession, *, project: Project, user_id: int, actor_user_id: int
) -> ProjectCapabilityGrant:
    """Delegate protocol management only to an existing project member."""
    membership = await db.get(UserToProject, (project.project_id, user_id))
    if membership is None:
        raise ProtocolConflictError("Protocol managers must be project members")
    grant = await db.get(
        ProjectCapabilityGrant,
        (project.project_id, user_id, ProjectCapability.MANAGE_PROTOCOLS),
    )
    if grant is None:
        grant = ProjectCapabilityGrant(
            project_id=project.project_id,
            user_id=user_id,
            capability=ProjectCapability.MANAGE_PROTOCOLS,
        )
        db.add(grant)
        db.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                project_id=project.project_id,
                action="project.capability.granted",
                resource_type="user",
                resource_id=str(user_id),
                details={"capability": ProjectCapability.MANAGE_PROTOCOLS.value},
            )
        )
        await db.flush()
    return grant


async def revoke_protocol_manager(
    db: AsyncSession, *, project: Project, user_id: int, actor_user_id: int
) -> None:
    """Revoke delegated protocol management without changing membership."""
    grant = await db.get(
        ProjectCapabilityGrant,
        (project.project_id, user_id, ProjectCapability.MANAGE_PROTOCOLS),
    )
    if grant is not None:
        await db.delete(grant)
        db.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                project_id=project.project_id,
                action="project.capability.revoked",
                resource_type="user",
                resource_id=str(user_id),
                details={"capability": ProjectCapability.MANAGE_PROTOCOLS.value},
            )
        )
        await db.flush()


async def validate_revision(
    db: AsyncSession,
    *,
    project: Project,
    revision_id: uuid.UUID,
) -> ValidationRun:
    """Persist deterministic evidence against the project's pinned protocol."""
    if project.protocol_version_id is None:
        raise ProtocolConflictError("Project has no published protocol version pinned")
    return await validate_revision_against_version(
        db,
        project=project,
        revision_id=revision_id,
        protocol_version_id=project.protocol_version_id,
    )


async def validate_revision_against_version(
    db: AsyncSession,
    *,
    project: Project,
    revision_id: uuid.UUID,
    protocol_version_id: uuid.UUID,
) -> ValidationRun:
    """Persist evidence for one revision against an explicit published version."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("Pinned protocol version is not published")
    revision = await db.scalar(
        select(EafRevision)
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(
            EafRevision.revision_id == revision_id,
            ElanFile.project_id == project.project_id,
        )
    )
    if revision is None:
        raise ProtocolNotFoundError("EAF revision not found")
    validator = await _validator_release(db)
    existing = await db.scalar(
        select(ValidationRun)
        .where(
            ValidationRun.revision_id == revision_id,
            ValidationRun.protocol_version_id == version.protocol_version_id,
            ValidationRun.validator_release_id == validator.validator_release_id,
        )
        .options(selectinload(ValidationRun.issues))
    )
    if existing is not None:
        return existing

    findings: list[tuple[str, ValidationSeverity, str, str, str | None]] = []
    try:
        root = validate_eaf(revision.raw_xml)
    except EafValidationError as error:
        findings.extend(
            (
                issue.code,
                ValidationSeverity.ERROR,
                issue.location,
                issue.message,
                None,
            )
            for issue in error.issues
        )
        root = None
    if root is not None:
        findings.extend(
            (
                finding.code,
                finding.severity,
                finding.location,
                finding.message,
                finding.rule_key,
            )
            for finding in evaluate_protocol_rules(
                root, ProtocolRules.model_validate(version.rules)
            )
        )

    run = ValidationRun(
        revision_id=revision_id,
        protocol_version_id=version.protocol_version_id,
        validator_release_id=validator.validator_release_id,
        outcome=(ValidationOutcome.FAILED if findings else ValidationOutcome.PASSED),
    )
    run.issues.extend(
        ProtocolValidationIssue(
            issue_number=index,
            code=code,
            severity=severity,
            location=location,
            message=message,
            rule_key=rule_key,
        )
        for index, (code, severity, location, message, rule_key) in enumerate(
            findings, start=1
        )
    )
    db.add(run)
    await db.flush()
    return run


async def run_compliance_scan(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    actor_user_id: int,
    trigger: str,
) -> ProjectComplianceScan:
    """Validate every latest accepted EAF revision and persist the snapshot."""
    version = await _scoped_version(
        db, project=project, protocol_version_id=protocol_version_id
    )
    if version.status != ProtocolVersionStatus.PUBLISHED:
        raise ProtocolConflictError("Compliance scans require a published protocol")
    if version.archive is not None:
        raise ProtocolConflictError("Archived protocol versions cannot start new scans")
    if trigger not in {"manual", "preview", "protocol_pinned"}:
        raise ProtocolConflictError("Unsupported compliance scan trigger")

    latest_number = (
        select(
            EafRevision.elan_id,
            func.max(EafRevision.revision_number).label("revision_number"),
        )
        .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
        .where(ElanFile.project_id == project.project_id)
        .group_by(EafRevision.elan_id)
        .subquery()
    )
    revisions = list(
        (
            await db.scalars(
                select(EafRevision)
                .join(
                    latest_number,
                    (latest_number.c.elan_id == EafRevision.elan_id)
                    & (latest_number.c.revision_number == EafRevision.revision_number),
                )
                .options(selectinload(EafRevision.elan_file))
                .order_by(EafRevision.elan_id)
            )
        ).all()
    )
    scan = ProjectComplianceScan(
        project_id=project.project_id,
        protocol_version_id=protocol_version_id,
        status="running",
        trigger=trigger,
        initiated_by=actor_user_id,
        total_files=len(revisions),
        files=[],
    )
    db.add(scan)
    await db.flush()
    for revision in revisions:
        run = await validate_revision_against_version(
            db,
            project=project,
            revision_id=revision.revision_id,
            protocol_version_id=protocol_version_id,
        )
        scan.files.append(
            ProjectComplianceScanFile(
                elan_id=revision.elan_id,
                revision_id=revision.revision_id,
                validation_run_id=run.validation_run_id,
                outcome=run.outcome,
            )
        )
        if run.outcome == ValidationOutcome.PASSED:
            scan.passed_files += 1
        else:
            scan.failed_files += 1
    scan.status = "completed"
    scan.completed_at = datetime.now(UTC)
    db.add(
        AuditEvent(
            actor_user_id=actor_user_id,
            project_id=project.project_id,
            action="project.compliance.scanned",
            resource_type="compliance_scan",
            resource_id=str(scan.scan_id),
            details={
                "trigger": trigger,
                "protocol_version_id": str(protocol_version_id),
                "total_files": scan.total_files,
                "failed_files": scan.failed_files,
            },
        )
    )
    await db.flush()
    return scan


async def list_compliance_scans(
    db: AsyncSession, *, project: Project, limit: int = 10
) -> list[ProjectComplianceScan]:
    """Return recent scans with all researcher-facing evidence loaded."""
    return list(
        (
            await db.scalars(
                select(ProjectComplianceScan)
                .where(ProjectComplianceScan.project_id == project.project_id)
                .options(
                    selectinload(ProjectComplianceScan.protocol_version).selectinload(
                        ProtocolVersion.protocol
                    ),
                    selectinload(ProjectComplianceScan.files).selectinload(
                        ProjectComplianceScanFile.elan_file
                    ),
                    selectinload(ProjectComplianceScan.files)
                    .selectinload(ProjectComplianceScanFile.validation_run)
                    .selectinload(ValidationRun.issues),
                )
                .order_by(ProjectComplianceScan.started_at.desc())
                .limit(limit)
            )
        )
        .unique()
        .all()
    )


def compliance_scan_response(scan: ProjectComplianceScan) -> ComplianceScanResponse:
    """Translate loaded persistence records into a stable API representation."""
    version = scan.protocol_version
    return ComplianceScanResponse(
        scan_id=scan.scan_id,
        project_id=scan.project_id,
        protocol_version_id=scan.protocol_version_id,
        protocol_name=version.protocol.name,
        protocol_version_number=version.version_number,
        status=scan.status,
        trigger=scan.trigger,
        total_files=scan.total_files,
        passed_files=scan.passed_files,
        failed_files=scan.failed_files,
        started_at=scan.started_at,
        completed_at=scan.completed_at,
        error_summary=scan.error_summary,
        files=[
            ComplianceScanFileResponse(
                scan_file_id=item.scan_file_id,
                elan_id=item.elan_id,
                revision_id=item.revision_id,
                filename=item.elan_file.filename,
                outcome=ValidationOutcome(item.outcome),
                validation_run_id=item.validation_run_id,
                issues=[
                    ValidationIssueResponse.model_validate(issue)
                    for issue in item.validation_run.issues
                ],
            )
            for item in sorted(scan.files, key=lambda value: value.elan_file.filename)
        ],
    )


async def _scoped_version(
    db: AsyncSession,
    *,
    project: Project,
    protocol_version_id: uuid.UUID,
    lock: bool = False,
) -> ProtocolVersion:
    statement = (
        select(ProtocolVersion)
        .join(Protocol, Protocol.protocol_id == ProtocolVersion.protocol_id)
        .where(
            ProtocolVersion.protocol_version_id == protocol_version_id,
            Protocol.instance_id == project.instance_id,
        )
        .options(selectinload(ProtocolVersion.archive))
    )
    if lock:
        statement = statement.with_for_update()
    version = await db.scalar(statement)
    if version is None:
        raise ProtocolNotFoundError("Protocol version not found")
    return version


async def _validator_release(db: AsyncSession) -> ValidatorRelease:
    checksum = hashlib.sha256(
        SCHEMA_PATH.read_bytes()
        + b"\0"
        + Path(__file__).read_bytes()
        + b"\0"
        + VALIDATOR_VERSION.encode("ascii")
    ).hexdigest()
    release = await db.scalar(
        select(ValidatorRelease).where(
            ValidatorRelease.name == VALIDATOR_NAME,
            ValidatorRelease.version == VALIDATOR_VERSION,
        )
    )
    if release is None:
        release = ValidatorRelease(
            name=VALIDATOR_NAME,
            version=VALIDATOR_VERSION,
            checksum_sha256=checksum,
        )
        db.add(release)
        await db.flush()
    elif release.checksum_sha256 != checksum:
        raise ProtocolConflictError(
            "Validator checksum changed without a validator version increment"
        )
    return release
