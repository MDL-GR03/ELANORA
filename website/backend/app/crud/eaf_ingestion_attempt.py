"""Persistence for rejected EAF ingestion attempts."""

import hashlib

from sqlalchemy.ext.asyncio import AsyncSession

from app.elan.validation import ValidationIssue
from app.model.eaf_ingestion_attempt import EafIngestionAttempt


def record_rejected_eaf(
    db: AsyncSession,
    *,
    instance_id: int,
    project_id: int | None,
    requested_project_name: str,
    filename: str,
    raw_xml: bytes,
    issues: tuple[ValidationIssue, ...],
    submitted_by: int | None,
) -> EafIngestionAttempt:
    """Stage an immutable rejected payload in the caller's transaction."""
    attempt = EafIngestionAttempt(
        instance_id=instance_id,
        project_id=project_id,
        submitted_by=submitted_by,
        requested_project_name=requested_project_name,
        filename=filename,
        sha256=hashlib.sha256(raw_xml).hexdigest(),
        file_size=len(raw_xml),
        raw_xml=raw_xml,
        validation_issues=[
            {"code": issue.code, "message": issue.message, "location": issue.location}
            for issue in issues
        ],
    )
    db.add(attempt)
    return attempt
