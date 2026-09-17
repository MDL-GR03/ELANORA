"""Typed response models for contribution queue."""

from typing import Any, TypedDict


class QueueItemFileCounts(TypedDict):
    """File counts for a queue item."""

    new: int
    modified: int
    deleted: int


class QueueItemFiles(TypedDict):
    """File lists for a queue item."""

    new: list[str]
    modified: list[str]
    deleted: list[str]


class QueueItemQualityChecks(TypedDict):
    """Quality check results for a queue item."""

    eaf: str
    naming: str
    protocol: str


class QueueItemSemanticSummary(TypedDict, total=False):
    """Semantic analysis summary for a queue item."""

    files: int
    annotations: int
    added: int
    removed: int
    value_changed: int
    timing_changed: int
    tier_changed: int


class QueueItemResearchContext(TypedDict, total=False):
    """Research context for a queue item."""

    summary: str | None
    topic_review_status: str | None
    changed_tiers: list[str]
    baseline_changed_tiers: list[str]
    outside_scope_tiers: list[str]
    scope_status: str
    declared_tiers: list[str]
    baseline_tiers: list[str]


class QueueItemProtocolWarning(TypedDict, total=False):
    """A protocol validation warning."""

    filename: str
    code: str
    message: str
    location: str
    rule_key: str


class AnnotationCollision(TypedDict):
    """Information about annotation conflicts between contributions."""

    contribution_id: int
    annotations: dict[str, list[str]]


class QueueItem(TypedDict, total=False):
    """A single item in the review queue."""

    upload_id: int
    branch_name: str | None
    original_branch: str | None
    upload_type: str
    description: str | None
    status: str
    uploaded_at: str | None
    uploaded_by: str | None
    files: QueueItemFiles
    file_counts: QueueItemFileCounts
    quality_checks: QueueItemQualityChecks
    protocol_warnings: list[QueueItemProtocolWarning]
    semantic_summary: QueueItemSemanticSummary
    research_context: QueueItemResearchContext
    protocol_version_id: str | None
    git_details: dict[str, Any] | None
    merge_status: str
    # Fields for specific states
    superseded_by_upload_id: int | None
    duplicate_of_upload_id: int | None
    conflicted_files: list[str] | None
    conflicted_files_count: int | None
    tested_at: str | None
    # Error state
    error: str | None
    can_auto_merge: bool | None
    # Annotation collisions
    annotation_collisions: list[AnnotationCollision]


class ReviewQueueResponse(TypedDict):
    """The complete review queue response."""

    project_name: str
    pending_uploads: list[QueueItem]
    total_pending: int
    ready_count: int
    conflicts_count: int
