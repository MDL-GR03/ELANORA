"""The Git API's shared services, dependencies and fixed messages.

Every Git route reaches its services through this module, so a test or an
operator has one place to point them somewhere else.
"""

from fastapi import Depends, File, Form

from app.core.centralized_logging import get_logger
from app.dependency.project_lock import project_write_lock
from app.service.contribution_change_set import ContributionChangeSetCoordinator
from app.service.git import GitService
from app.service.project_sync import ProjectSyncCoordinator

project_lock_dep = Depends(project_write_lock)

git_service = GitService()
contribution_change_sets = ContributionChangeSetCoordinator(git_service)

# Deleted projects stay restorable by name, so their names remain reserved.
# Recovery only replaces or discards storage that is actually missing.
sync_coordinator = ProjectSyncCoordinator(git_service)
logger = get_logger()

eaf_upload_files_dep = File(...)
correction_case_id_dep = Form(default=None)
