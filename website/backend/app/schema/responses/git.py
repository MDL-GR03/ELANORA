from typing import Any

from pydantic import Field

from app.schema.common.base import CustomBaseModel
from app.schema.common.git import FileStatus


class GitStatusResponse(CustomBaseModel):
    """Schema for Git availability status."""

    git_available: bool
    version: str | None = None
    status: str
    error: str | None = None


class ProjectCreateResponse(CustomBaseModel):
    """Schema for project creation response."""

    project_name: str
    path: str
    status: str
    git_initialized: bool
    created_at: str


class FileUploadResponse(CustomBaseModel):
    """Schema for file upload response."""

    filename: str
    project_name: str
    status: str
    branch_name: str
    file_existed: bool
    merge_status: str
    has_conflicts: bool
    conflicts: list[str] | None = None
    added_at: str


class UploadedFileInfo(CustomBaseModel):
    filename: str
    size: int | None = None
    existed: bool


class FailedFileInfo(CustomBaseModel):
    filename: str
    error: str


class EafValidationIssueResponse(CustomBaseModel):
    """One machine-readable EAF validation issue returned to a researcher."""

    code: str
    message: str
    location: str


class RejectedEafFileResponse(CustomBaseModel):
    """Validation summary for one quarantined source file."""

    filename: str
    sha256: str
    issue_count: int
    issues: list[EafValidationIssueResponse]


class DiffChange(CustomBaseModel):
    type: str  # "addition", "deletion", "context"
    line_number: int | None = None
    line_number_old: int | None = None
    line_number_new: int | None = None
    content: str


class DiffHunk(CustomBaseModel):
    old_start: int
    new_start: int
    old_count: int
    new_count: int
    context: str
    changes: list[DiffChange]


class FileChanges(CustomBaseModel):
    filename: str
    added_lines: list[DiffChange]
    removed_lines: list[DiffChange]
    modified_sections: list[dict[str, object]] = Field(default_factory=list)
    total_additions: int
    total_deletions: int
    hunks: list[DiffHunk]
    summary: str
    diff_raw: str
    error: str | None = None


class UploadSummary(CustomBaseModel):
    """Schema for upload file summary."""

    new_files: list[str] = Field(default_factory=list)
    modified_files: list[str] = Field(default_factory=list)
    deleted_files: list[str] = Field(default_factory=list)


class AdminInfo(CustomBaseModel):
    """Schema for admin workflow information."""

    pending_approval_since: str | None = None
    approval_branch: str | None = None
    original_branch: str | None = None
    next_steps: str | None = None


class BatchFileUploadResponse(CustomBaseModel):
    project_name: str
    upload_id: int
    branch_name: str | None = None
    uploaded_files: list[UploadedFileInfo]
    failed_files: list[FailedFileInfo]
    total_uploaded: int
    total_failed: int
    existing_files_updated: int
    new_files_added: int

    # Workflow status fields (updated for pending upload workflow)
    status: str  # "pending_admin_approval"
    requires_approval: bool = True
    has_differences: bool = False
    auto_accepted: bool = False

    # Legacy fields for backward compatibility
    merge_status: str = "pending_admin_approval"  # Default value
    has_conflicts: bool = False  # No conflicts until admin tests merge
    conflicts: list[FileChanges] = Field(default_factory=list)

    # New workflow fields
    upload_summary: UploadSummary | None = None
    admin_info: AdminInfo | None = None

    # Optional fields
    new_files_in_merge: list[str] | None = Field(default_factory=list)
    modified_files_in_merge: list[str] | None = Field(default_factory=list)
    uploaded_at: str
    message: str | None = None


class ProjectInfo(CustomBaseModel):
    project_id: int
    project_name: str
    project_description: str | None = None
    permission: str | None = None
    auto_accept_new_files: bool = False
    capabilities: list[str] = Field(default_factory=list)


class ProjectListResponse(CustomBaseModel):
    projects: list[ProjectInfo]


class ProjectEditResponse(CustomBaseModel):
    """Schema for project edit response."""

    new_project_name: str
    new_project_description: str | None = None


class ProjectSyncCheckResponse(CustomBaseModel):
    """Schema for project synchronization check response."""

    project_name: str
    in_sync: bool
    files_status: list[FileStatus] = Field(default_factory=list)
    status: str | None = None


class ProjectSyncExecutionResponse(ProjectSyncCheckResponse):
    """Result linked to its durable cross-system operation record."""

    operation_id: str


class PendingUploadInfo(CustomBaseModel):
    """Schema for individual pending upload information."""

    upload_id: int
    branch_name: str
    original_branch: str | None = None
    upload_type: str
    description: str
    status: str
    uploaded_at: str | None = None
    uploaded_by: str | None = None
    files: dict[str, list[str]] = Field(default_factory=dict)
    file_counts: dict[str, int] = Field(default_factory=dict)
    semantic_summary: dict[str, int] = Field(default_factory=dict)
    research_context: dict[str, Any] = Field(default_factory=dict)
    annotation_collisions: list[dict[str, Any]] = Field(default_factory=list)
    quality_checks: dict[str, str] = Field(default_factory=dict)
    # Non-blocking protocol findings recorded when the contribution was submitted.
    protocol_warnings: list[dict[str, str | None]] = Field(default_factory=list)
    protocol_version_id: str | None = None
    duplicate_of_upload_id: int | None = None
    superseded_by_upload_id: int | None = None

    # Real-time merge status (computed when requested)
    merge_status: str | None = None  # "ready_to_merge", "needs_resolution", "error"
    conflicted_files: list[str] = Field(default_factory=list)
    conflicted_files_count: int = 0
    tested_at: str | None = None

    # Raw git details
    git_details: dict[str, object] | None = None


class PendingUploadsResponse(CustomBaseModel):
    """Schema for pending uploads list response."""

    project_name: str
    pending_uploads: list[PendingUploadInfo]
    total_pending: int
    ready_count: int = 0
    conflicts_count: int = 0


class AcceptedProjectVersion(CustomBaseModel):
    """One immutable commit on the canonical project branch."""

    commit: str
    short_commit: str
    committed_at: str
    message: str
    author: str
    action: str
    contribution_id: int | None = None
    restored_from: str | None = None
    reason: str | None = None
    is_current: bool = False


class AcceptedProjectHistoryResponse(CustomBaseModel):
    project_name: str
    current_commit: str
    versions: list[AcceptedProjectVersion]


class ProjectVersionFileChange(CustomBaseModel):
    status: str
    filename: str


class ProjectVersionPreviewResponse(CustomBaseModel):
    project_name: str
    current_commit: str
    target_commit: str
    files: list[ProjectVersionFileChange]
    semantic_summary: dict[str, int] = Field(default_factory=dict)
    affected_pending_contributions: int = 0
    affected_pending_upload_ids: list[int] = Field(default_factory=list)
    active_review_cases: int = 0
    active_review_case_ids: list[str] = Field(default_factory=list)


class ProjectVersionRestoreResponse(CustomBaseModel):
    project_name: str
    previous_commit: str
    target_commit: str
    restored_commit: str
    status: str


class ProjectRevisionHealthResponse(CustomBaseModel):
    project_name: str
    revision_id: str | None = None
    git_commit: str
    status: str
    recoverable: bool
    git_export_matches: bool = True
    detail: str | None = None
    missing_files: list[str] = Field(default_factory=list)
    unexpected_files: list[str] = Field(default_factory=list)
    checksum_mismatches: list[str] = Field(default_factory=list)
    database_missing_files: list[str] = Field(default_factory=list)
    database_unexpected_files: list[str] = Field(default_factory=list)
    database_checksum_mismatches: list[str] = Field(default_factory=list)


class ProjectRevisionRecoveryResponse(CustomBaseModel):
    project_name: str
    revision_id: str
    manifest_sha256: str
    file_count: int
    status: str


class AnnotationReviewSnapshot(CustomBaseModel):
    """One annotation state displayed in a semantic contribution review."""

    annotation_id: str
    tier_id: str
    value: str
    start_ms: int | None = None
    end_ms: int | None = None
    annotation_ref: str | None = None


class AnnotationReviewChange(CustomBaseModel):
    """A researcher-readable change to an EAF annotation."""

    annotation_id: str
    kinds: list[str]
    before: AnnotationReviewSnapshot | None = None
    after: AnnotationReviewSnapshot | None = None


class EafReviewResponse(CustomBaseModel):
    """Semantic comparison used by the read-only EAF review preview."""

    changes: list[AnnotationReviewChange]
    before_media_urls: list[str]
    after_media_urls: list[str]


class FileInfo(CustomBaseModel):
    name: str
    size: int
    last_modified: str = Field(alias="lastModified")
    last_updated_by: str = Field(alias="lastUpdatedBy")
    type: str = "file"


class ProjectFilesResponse(CustomBaseModel):
    files: list[FileInfo]


class FileInfoWithMedia(CustomBaseModel):
    """Extended file info that includes database ID and associated media filenames."""

    name: str
    size: int
    last_modified: str = Field(alias="lastModified")
    last_updated_by: str = Field(alias="lastUpdatedBy")
    type: str = "file"
    elan_id: int | None = None  # Database ID for rename operations
    media_filenames: list[str] = Field(default_factory=list)


class ProjectFilesWithMediaResponse(CustomBaseModel):
    """Response for project files that includes media information."""

    files: list[FileInfoWithMedia]


class RenameResult(CustomBaseModel):
    """Schema for individual file rename result."""

    old_filename: str
    new_filename: str
    success: bool
    error: str | None = None
    conflict_elan_id: int | None = None
    message_key: str | None = None


class FileRenameResponse(CustomBaseModel):
    """Schema for single file rename response."""

    project_name: str
    old_filename: str
    new_filename: str
    success: bool
    committed: bool
    commit_hash: str | None = None
    renamed_at: str
    message: str | None = None
    conflict_elan_id: int | None = None
    message_key: str | None = None


class BulkRenameResponse(CustomBaseModel):
    """Schema for bulk file rename response."""

    project_name: str
    total_files: int
    successful_renames: int
    failed_renames: int
    results: list[RenameResult]
    committed: bool
    commit_hash: str | None = None
    renamed_at: str
    message: str | None = None
    conflicts_count: int = 0
    message_key: str | None = None
