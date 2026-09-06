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


class ContributionPolicyRequest(CustomBaseModel):
    """Safe automatic-acceptance settings for one project."""

    auto_accept_new_files: bool
