"""What unattended maintenance this installation has actually done."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class MaintenanceRun(Base):
    """One attempt at a scheduled job, kept so the schedule survives restarts.

    The next run is decided from these rows rather than from a timer in memory,
    so restarting the installation never repeats a backup and never silently
    skips one.
    """

    __tablename__ = "MAINTENANCE_RUN"
    __table_args__ = (
        CheckConstraint(
            "job IN ('backup', 'backup_verification', 'retention_purge', "
            "'storage_capacity')",
            name="ck_maintenance_run_job",
        ),
        CheckConstraint(
            "outcome IN ('succeeded', 'failed', 'skipped')",
            name="ck_maintenance_run_outcome",
        ),
        CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_maintenance_run_interval",
        ),
        Index("ix_maintenance_run_job_started", "job", "started_at"),
    )

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    job: Mapped[str] = mapped_column(String(40), nullable=False)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Never holds participant data: counts, object keys, and error types only.
    detail: Mapped[dict[str, object]] = mapped_column(
        JSON, nullable=False, default=dict
    )
