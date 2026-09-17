"""Typed response models for contribution intake."""

from typing import Any, TypedDict


class ProtocolValidation(TypedDict, total=False):
    """Protocol validation results for a submission."""

    outcome: str
    warnings: list[dict[str, Any]]
    protocol_version_id: str | None


class ResearchContext(TypedDict, total=False):
    """Research scope context declared for a submission."""

    summary: str | None
    topic_review_status: str | None
    declared_tiers: list[str]
    baseline_tiers: list[str]


class UploadInfoResponse(TypedDict, total=False):
    """Information about a pending upload submission."""

    upload_id: int
    status: str
    has_conflicts: bool
    has_differences: bool
    requires_approval: bool
    auto_accepted: bool
    branch_name: str
    original_branch: str
    new_files: list[str]
    modified_files: list[str]
    deleted_files: list[str]
    message: str
    pending_approval_since: str
    uploaded_by: str
    base_commit: str
    protocol_validation: ProtocolValidation
    research_context: ResearchContext
