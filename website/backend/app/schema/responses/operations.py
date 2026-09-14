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


class PublicationQueueStatusResponse(BaseModel):
    queued: int
    running: int
    review_needed: int
    failed: int


class EmailDeliveryStatusResponse(BaseModel):
    pending: int
    permanently_failed: int
    oldest_pending_at: datetime | None
    retention_days: int


class OperationsStatusResponse(BaseModel):
    storage: StorageStatusResponse
    integrity: IntegrityStatusResponse
    recovery: RecoveryStatusResponse
    publication_queue: PublicationQueueStatusResponse
    email_delivery: EmailDeliveryStatusResponse


class StorageCheckResponse(BaseModel):
    status: str
    checked_at: datetime
