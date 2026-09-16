"""The Git API, assembled from one router per area."""

from fastapi import APIRouter

from app.api.v1 import (
    git_contributions,
    git_file_names,
    git_history,
    git_projects,
    git_sync,
)

router = APIRouter()
for area in (git_projects, git_contributions, git_history, git_sync, git_file_names):
    router.include_router(area.router)
