"""Add durable project synchronization operations.

Revision ID: 0009
Revises: 0008
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "PROJECT_SYNC_OPERATION",
        sa.Column("operation_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("initiated_by", sa.Integer(), nullable=True),
        sa.Column("state", sa.String(32), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("evidence_manifest", sa.JSON(), nullable=False),
        sa.Column("staging_key", sa.String(255), nullable=True),
        sa.Column("starting_commit", sa.String(64), nullable=True),
        sa.Column("resulting_commit", sa.String(64), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('preparing','prepared','committing','completed','discarded','failed','recovery_required')",
            name="ck_project_sync_operation_state",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["initiated_by"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("operation_id"),
    )
    op.create_index(
        "ix_project_sync_operation_project_id", "PROJECT_SYNC_OPERATION", ["project_id"]
    )
    op.create_index(
        "ix_project_sync_operation_state", "PROJECT_SYNC_OPERATION", ["state"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_sync_operation_state", table_name="PROJECT_SYNC_OPERATION"
    )
    op.drop_index(
        "ix_project_sync_operation_project_id", table_name="PROJECT_SYNC_OPERATION"
    )
    op.drop_table("PROJECT_SYNC_OPERATION")
