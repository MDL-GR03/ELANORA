"""Record the unattended maintenance this installation performs.

An institution installs ELANORA and does not staff a platform team. The
installation therefore takes its own backups, verifies them, applies its
retention policy and watches its disk, and records each attempt here so the
schedule survives restarts and an administrator can see the real state.

Revision ID: 0037
Revises: 0036
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0037"
down_revision: str | None = "0036"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "MAINTENANCE_RUN",
        sa.Column("run_id", sa.Uuid(), nullable=False),
        sa.Column("job", sa.String(length=40), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
        sa.CheckConstraint(
            "job IN ('backup', 'backup_verification', 'retention_purge', "
            "'storage_capacity')",
            name="ck_maintenance_run_job",
        ),
        sa.CheckConstraint(
            "outcome IN ('succeeded', 'failed', 'skipped')",
            name="ck_maintenance_run_outcome",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR finished_at >= started_at",
            name="ck_maintenance_run_interval",
        ),
    )
    op.create_index(
        "ix_maintenance_run_job_started", "MAINTENANCE_RUN", ["job", "started_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_maintenance_run_job_started", table_name="MAINTENANCE_RUN")
    op.drop_table("MAINTENANCE_RUN")
