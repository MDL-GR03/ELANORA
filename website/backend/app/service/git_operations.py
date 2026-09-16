"""Git operations, grouped by what each collaborator does.

The work lives in focused modules: command execution, branches and their
differences, merging, and writing uploaded files. This module keeps the names
its callers already import.
"""

from app.service.git_branches import GitBranchManager, GitDiffAnalyzer
from app.service.git_command_runner import (
    GitCommandRunner,
    WorkingTreeOffAcceptedBranchError,
    delete_project_folder,
)
from app.service.git_merge import GitMerger
from app.service.git_results import FileUploadResult, MergeAnalysis, MergeReadiness
from app.service.git_uploads import FileUploadProcessor

__all__ = [
    "FileUploadProcessor",
    "FileUploadResult",
    "GitBranchManager",
    "GitCommandRunner",
    "GitDiffAnalyzer",
    "GitMerger",
    "MergeAnalysis",
    "MergeReadiness",
    "WorkingTreeOffAcceptedBranchError",
    "delete_project_folder",
]
