import uuid
from typing import Literal

from pydantic import Field

from app.schema.common.base import CustomBaseModel


class ProjectCreateRequest(CustomBaseModel):
    """Schema for project creation request."""

    project_name: str
    description: str | None = None


class ProjectEditRequest(CustomBaseModel):
    """Schema for project edit request."""

    new_project_name: str
    new_project_description: str | None = None


class FileRename(CustomBaseModel):
    """Schema for a single file rename operation."""

    elan_id: int
    new_filename: str


class BulkRenameRequest(CustomBaseModel):
    """Schema for bulk file rename request."""

    renames: list[FileRename]


class PendingUploadMergeRequest(CustomBaseModel):
    """An administrator's explicit strategy for a reviewed contribution."""

    resolution_strategy: Literal["auto", "accept_incoming", "accept_current"] = "auto"


class PendingUploadDeclineRequest(CustomBaseModel):
    """An administrator's reason for terminally declining a contribution."""

    reason: str = Field(min_length=3, max_length=1000)


class ContributionResearchTopicRequest(CustomBaseModel):
    """An administrator's decision on a contribution's research classification."""

    topic_id: int | None = None
    new_topic_name: str | None = Field(default=None, min_length=2, max_length=100)


class ContributionPolicyRequest(CustomBaseModel):
    """Safe automatic-acceptance settings for one project."""

    auto_accept_new_files: bool


class ProjectVersionPreviewRequest(CustomBaseModel):
    """Select an immutable canonical revision for a restoration preview."""

    target_commit: str = Field(min_length=7, max_length=64)


class ProjectVersionRestoreRequest(ProjectVersionPreviewRequest):
    """Create a new canonical commit whose tree matches an earlier revision."""

    expected_head: str = Field(min_length=40, max_length=64)
    reason: str = Field(min_length=10, max_length=2000)
    confirmation: str = Field(min_length=1, max_length=200)


class ProjectRevisionRecoveryRequest(CustomBaseModel):
    """Explicit authorization to repair the current accepted project state."""

    revision_id: uuid.UUID
    reason: str = Field(min_length=10, max_length=2000)
    confirmation: str = Field(min_length=1, max_length=200)
