"""Administrator-safe operational status responses."""

from datetime import datetime

from pydantic import BaseModel


class StorageStatusResponse(BaseModel):
    backend: str
    location_hint: str
    credentials_source: str
    policy_verification: str


class IntegrityStatusResponse(BaseModel):
    total_projects: int
    scanned_projects: int
    healthy_projects: int
    unhealthy_projects: int
    unscanned_projects: int
    latest_check_at: datetime | None


class RecoveryStatusResponse(BaseModel):
    responsibility: str
    latest_drill_at: datetime | None
    state: str


class OperationsStatusResponse(BaseModel):
    storage: StorageStatusResponse
    integrity: IntegrityStatusResponse
    recovery: RecoveryStatusResponse


class StorageCheckResponse(BaseModel):
    status: str
    checked_at: datetime
