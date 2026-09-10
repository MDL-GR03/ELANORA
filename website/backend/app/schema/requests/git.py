from pydantic import Field

from app.schema.common.base import CustomBaseModel


class ProjectCreateRequest(CustomBaseModel):
    """Schema for project creation request."""

    project_name: str
    description: str | None = None


class CommitRequest(CustomBaseModel):
    """Schema for commit request."""

    commit_message: str
    user_name: str = "user"


class ProjectCheckoutRequest(CustomBaseModel):
    """Schema for project branch checkout request."""

    branch_name: str


class ProjectEditRequest(CustomBaseModel):
    """Schema for project edit request."""

    new_project_name: str
    new_project_description: str | None = None


class ProjectDeleteRequest(CustomBaseModel):
    """Schema for project delete request."""

    project_id: int
    confirm: bool = False


class FileRename(CustomBaseModel):
    """Schema for a single file rename operation."""

    elan_id: int
    new_filename: str


class BulkRenameRequest(CustomBaseModel):
    """Schema for bulk file rename request."""

    renames: list[FileRename]


class PendingUploadMergeRequest(CustomBaseModel):
    """An administrator's explicit strategy for a reviewed contribution."""

    resolution_strategy: str = "auto"


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
