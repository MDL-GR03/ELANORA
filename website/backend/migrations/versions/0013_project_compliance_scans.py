"""Add durable project compliance scan snapshots.

Revision ID: 0013
Revises: 0012
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "REVIEW_CASE", "upload_id", existing_type=sa.Integer(), nullable=True
    )
    op.create_table(
        "PROJECT_COMPLIANCE_SCAN",
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("protocol_version_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("trigger", sa.String(length=24), nullable=False),
        sa.Column("initiated_by", sa.Integer(), nullable=True),
        sa.Column("total_files", sa.Integer(), nullable=False),
        sa.Column("passed_files", sa.Integer(), nullable=False),
        sa.Column("failed_files", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_compliance_scan_status",
        ),
        sa.CheckConstraint(
            "trigger IN ('manual', 'preview', 'protocol_pinned')",
            name="ck_compliance_scan_trigger",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["protocol_version_id"],
            ["PROTOCOL_VERSION.protocol_version_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("scan_id"),
    )
    op.create_index(
        "ix_compliance_scan_project_started",
        "PROJECT_COMPLIANCE_SCAN",
        ["project_id", "started_at"],
    )
    op.create_table(
        "PROJECT_COMPLIANCE_SCAN_FILE",
        sa.Column("scan_file_id", sa.Uuid(), nullable=False),
        sa.Column("scan_id", sa.Uuid(), nullable=False),
        sa.Column("elan_id", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("validation_run_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('passed', 'failed')", name="ck_compliance_file_outcome"
        ),
        sa.ForeignKeyConstraint(
            ["scan_id"], ["PROJECT_COMPLIANCE_SCAN.scan_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["elan_id"], ["ELAN_FILE.elan_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["EAF_REVISION.revision_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["VALIDATION_RUN.validation_run_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("scan_file_id"),
        sa.UniqueConstraint("scan_id", "elan_id", name="uq_compliance_scan_file"),
    )
    op.create_index(
        "ix_compliance_scan_file_scan_outcome",
        "PROJECT_COMPLIANCE_SCAN_FILE",
        ["scan_id", "outcome"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_compliance_scan_file_scan_outcome",
        table_name="PROJECT_COMPLIANCE_SCAN_FILE",
    )
    op.drop_table("PROJECT_COMPLIANCE_SCAN_FILE")
    op.drop_index(
        "ix_compliance_scan_project_started", table_name="PROJECT_COMPLIANCE_SCAN"
    )
    op.drop_table("PROJECT_COMPLIANCE_SCAN")
    op.alter_column(
        "REVIEW_CASE", "upload_id", existing_type=sa.Integer(), nullable=False
    )
