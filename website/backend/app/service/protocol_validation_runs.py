"""Recording immutable validation evidence for a revision."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.elan.validation import EafValidationError, validate_eaf
from app.model.eaf_revision import EafRevision
from app.model.elan_file import ElanFile
from app.model.enums import (
    ProtocolVersionStatus,
    ValidationOutcome,
    ValidationSeverity,
)
from app.model.project import Project
from app.model.protocol import (
    ProtocolValidationIssue,
    ValidationRun,
    ValidatorRelease,
)
from app.schema.protocol import (
    ProtocolRules,
)
from app.service.protocol_errors import (
    ProtocolConflictError,
    ProtocolNotFoundError,
)
from app.service.protocol_evaluation import (
    VALIDATOR_NAME,
    VALIDATOR_VERSION,
    evaluate_protocol_rules,
    validator_checksum,
)
from app.service.protocol_shared import _scoped_version

FULL_COVERAGE_PERCENT = 100.0


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
    located = (
        await db.execute(
            select(EafRevision, ElanFile.filename)
            .join(ElanFile, ElanFile.elan_id == EafRevision.elan_id)
            .where(
                EafRevision.revision_id == revision_id,
                ElanFile.project_id == project.project_id,
            )
        )
    ).first()
    if located is None:
        raise ProtocolNotFoundError("EAF revision not found")
    revision, filename = located
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
                root, ProtocolRules.model_validate(version.rules), filename=filename
            )
        )

    run = ValidationRun(
        revision_id=revision_id,
        protocol_version_id=version.protocol_version_id,
        validator_release_id=validator.validator_release_id,
        outcome=(
            ValidationOutcome.FAILED
            if any(severity == ValidationSeverity.ERROR for _, severity, *_ in findings)
            else ValidationOutcome.PASSED
        ),
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
    # A run without issues leaves the collection unloaded, which serialization
    # cannot load from an async session.
    await db.refresh(run, attribute_names=["issues"])
    return run


async def _validator_release(db: AsyncSession) -> ValidatorRelease:
    checksum = validator_checksum()
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
