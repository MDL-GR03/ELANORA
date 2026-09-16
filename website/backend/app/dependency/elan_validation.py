import uuid
from dataclasses import dataclass

from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.config import ELAN_MAX_BATCH_SIZE_MB, ELAN_MAX_FILE_SIZE_MB
from app.core.errors import ElanoraError, ErrorCode
from app.crud.eaf_ingestion_attempt import record_rejected_eaf
from app.elan.validation import EafValidationError, ValidationIssue, validate_eaf
from app.model.project import Project
from app.model.protocol import ProtocolVersion
from app.schema.responses.git import (
    EafValidationIssueResponse,
    RejectedEafFileResponse,
)
from app.service.protocol_errors import ProtocolConflictError
from app.service.protocol_evaluation import (
    blocking_findings,
    validate_content_against_protocol,
)
from app.service.protocol_shared import get_pinned_protocol_version

logger = get_logger()
MAX_RETURNED_ISSUES = 20
MAX_RECORDED_WARNINGS = 200


@dataclass(frozen=True, slots=True)
class ValidatedEafBatch:
    """Validated uploads plus the immutable project protocol used to check them."""

    files: list[UploadFile]
    protocol_version_id: uuid.UUID | None
    protocol_rules_sha256: str | None
    protocol_outcome: str
    # Non-blocking protocol findings, kept with the contribution for reviewers.
    protocol_warnings: list[dict[str, str | None]]


async def _pinned_protocol(
    db: AsyncSession, project_id: int | None
) -> ProtocolVersion | None:
    if project_id is None:
        return None
    project = await db.get(Project, project_id)
    if project is None:
        raise ElanoraError(ErrorCode.PROJECT_NOT_FOUND)
    try:
        return await get_pinned_protocol_version(db, project)
    except ProtocolConflictError as error:
        raise ElanoraError(ErrorCode.PROTOCOL_CONFIGURATION_CONFLICT) from error


def _validate_batch_envelope(files: list[UploadFile]) -> int:
    """Validate declared batch metadata and return the byte limit."""
    if not files:
        raise ElanoraError(ErrorCode.UPLOAD_EMPTY)
    max_batch_size = ELAN_MAX_BATCH_SIZE_MB * 1024 * 1024
    if sum(file.size or 0 for file in files) > max_batch_size:
        raise ElanoraError(
            ErrorCode.UPLOAD_BATCH_TOO_LARGE, max_mb=ELAN_MAX_BATCH_SIZE_MB
        )
    return max_batch_size


async def _read_bounded_content(file: UploadFile) -> bytes:
    """Read one upload, enforce the actual size, and rewind it for storage."""
    content = await file.read()
    file.size = len(content)
    file.file.seek(0)
    if len(content) > ELAN_MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ElanoraError(
            ErrorCode.UPLOAD_FILE_TOO_LARGE, max_mb=ELAN_MAX_FILE_SIZE_MB
        )
    return content


def validate_elan_file(file: UploadFile) -> UploadFile:
    """Validate uploaded ELAN file.

    Args:
        file: The uploaded file

    Returns:
        The validated file

    Raises:
        ElanoraError: If file validation fails

    """
    # Check file extension
    if not file.filename or not file.filename.lower().endswith(".eaf"):
        raise ElanoraError(ErrorCode.UPLOAD_EXTENSION_REFUSED)

    # Upload names are untrusted input. Project uploads are deliberately flat, so
    # accepting path components would permit writes outside of ``elan_files``.
    if (
        file.filename in {".", ".."}
        or "/" in file.filename
        or "\\" in file.filename
        or "\x00" in file.filename
    ):
        raise ElanoraError(ErrorCode.EAF_FILENAME_INVALID)

    # Check file size (max 50MB per file - generous for ELAN files)
    max_file_size = ELAN_MAX_FILE_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_file_size:
        raise ElanoraError(
            ErrorCode.UPLOAD_FILE_TOO_LARGE, max_mb=ELAN_MAX_FILE_SIZE_MB
        )

    logger.info(f"Debug MIME type for file: {file.filename} - {file.content_type}")

    # Check content type only if it's suspicious, best practice as it allows not-known types of eaf files
    if file.content_type:
        # Block obviously dangerous types
        dangerous_types = [
            "application/javascript",
            "text/javascript",
            "application/x-executable",
            "application/x-msdownload",
            "text/html",
        ]

        if file.content_type in dangerous_types:
            raise ElanoraError(ErrorCode.UPLOAD_CONTENT_TYPE_REFUSED)

    return file


async def validate_multiple_elan_files(files: list[UploadFile]) -> list[UploadFile]:
    """Validate multiple ELAN files with no count limit.

    Args:
        files: List of uploaded files

    Returns:
        List of validated files

    Raises:
        ElanoraError: If validation fails

    """
    max_total_size = _validate_batch_envelope(files)

    # Validate each file individually
    validated_files = []
    actual_total_size = 0
    for file in files:
        validate_elan_file(file)
        validated_files.append(await validate_elan_file_content(file))
        actual_total_size += file.size or 0
        if actual_total_size > max_total_size:
            raise ElanoraError(
                ErrorCode.UPLOAD_BATCH_TOO_LARGE, max_mb=ELAN_MAX_BATCH_SIZE_MB
            )

    return validated_files


async def validate_elan_file_content(file: UploadFile) -> UploadFile:
    """Validate ELAN file content structure (advanced validation).

    Args:
        file: The uploaded file

    Returns:
        The validated file with reset file pointer

    Raises:
        ElanoraError: If file content validation fails

    """
    try:
        content = await _read_bounded_content(file)
        validate_eaf(content)

        return file

    except EafValidationError as e:
        summary = "; ".join(str(issue) for issue in e.issues[:10])
        remaining = len(e.issues) - 10
        if remaining > 0:
            summary = f"{summary}; and {remaining} more issue(s)"
        raise ElanoraError(ErrorCode.UPLOAD_EAF_INVALID, summary=summary) from e
    except (HTTPException, ElanoraError):
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.UPLOAD_VALIDATION_FAILED) from e


async def validate_and_record_elan_files(
    files: list[UploadFile],
    *,
    db: AsyncSession,
    instance_id: int,
    project_id: int | None,
    requested_project_name: str,
    submitted_by: int | None,
) -> ValidatedEafBatch:
    """Validate a batch and retain rejected EAF bytes outside canonical history."""
    max_batch_size = _validate_batch_envelope(files)
    protocol_version = await _pinned_protocol(db, project_id)

    validated: list[UploadFile] = []
    rejected: list[RejectedEafFileResponse] = []
    warnings: list[dict[str, str | None]] = []
    actual_size = 0
    for file in files:
        validate_elan_file(file)
        content = await _read_bounded_content(file)
        actual_size += len(content)
        if actual_size > max_batch_size:
            raise ElanoraError(
                ErrorCode.UPLOAD_BATCH_TOO_LARGE, max_mb=ELAN_MAX_BATCH_SIZE_MB
            )
        try:
            if protocol_version is None:
                validate_eaf(content)
                protocol_findings = ()
            else:
                protocol_findings = validate_content_against_protocol(
                    content, protocol_version, filename=file.filename or ""
                )
            blocking = blocking_findings(protocol_findings)
            if blocking:
                raise EafValidationError(
                    tuple(
                        ValidationIssue(
                            code=finding.code,
                            message=finding.message,
                            location=finding.location,
                        )
                        for finding in blocking
                    )
                )
            warnings.extend(
                {
                    "filename": file.filename,
                    "code": finding.code,
                    "message": finding.message,
                    "location": finding.location,
                    "rule_key": finding.rule_key,
                }
                for finding in protocol_findings
                if finding not in blocking
            )
        except EafValidationError as error:
            filename = file.filename or "unnamed.eaf"
            attempt = record_rejected_eaf(
                db,
                instance_id=instance_id,
                project_id=project_id,
                requested_project_name=requested_project_name,
                filename=filename,
                raw_xml=content,
                issues=error.issues,
                submitted_by=submitted_by,
            )
            rejected.append(
                RejectedEafFileResponse(
                    filename=filename,
                    sha256=attempt.sha256,
                    issue_count=len(error.issues),
                    issues=[
                        EafValidationIssueResponse(
                            code=issue.code,
                            message=issue.message,
                            location=issue.location,
                        )
                        for issue in error.issues[:MAX_RETURNED_ISSUES]
                    ],
                )
            )
        else:
            validated.append(file)

    if rejected:
        await db.commit()
        raise ElanoraError(
            ErrorCode.INVALID_EAF_BATCH,
            rejected_files=[file.model_dump(mode="json") for file in rejected],
        )

    return ValidatedEafBatch(
        files=validated,
        protocol_version_id=(
            protocol_version.protocol_version_id if protocol_version else None
        ),
        protocol_rules_sha256=(
            protocol_version.rules_sha256 if protocol_version else None
        ),
        protocol_outcome="passed" if protocol_version else "not_configured",
        protocol_warnings=warnings[:MAX_RECORDED_WARNINGS],
    )
