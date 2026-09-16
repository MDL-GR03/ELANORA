"""Authentication, assembled from one router per area."""

from fastapi import APIRouter

from app.api.v1 import auth_recovery, auth_registration, auth_sessions

router = APIRouter()
for area in (auth_sessions, auth_registration, auth_recovery):
    router.include_router(area.router)
