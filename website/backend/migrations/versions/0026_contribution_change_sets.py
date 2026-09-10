"""Add durable contribution publication change sets.

Revision ID: 0026
Revises: 0025
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0026"
down_revision: str | None = "0025"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "CONTRIBUTION_CHANGE_SET",
        sa.Column("change_set_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("requested_by", sa.Integer(), nullable=True),
        sa.Column("branch_name", sa.String(length=255), nullable=False),
        sa.Column("resolution_strategy", sa.String(length=32), nullable=False),
        sa.Column("expected_commit", sa.String(length=64), nullable=False),
        sa.Column("resulting_commit", sa.String(length=64), nullable=True),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "resolution_strategy IN ('auto','accept_incoming','accept_current')",
            name="ck_contribution_change_set_resolution_strategy",
        ),
        sa.CheckConstraint(
            "state IN ('queued','running','completed','review_needed','failed')",
            name="ck_contribution_change_set_state",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["requested_by"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["upload_id"], ["PENDING_UPLOAD.upload_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("change_set_id"),
    )
    op.create_index(
        "ix_contribution_change_set_state",
        "CONTRIBUTION_CHANGE_SET",
        ["state", "created_at"],
        unique=False,
    )
    op.create_index(
        "uq_contribution_change_set_upload_id",
        "CONTRIBUTION_CHANGE_SET",
        ["upload_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_contribution_change_set_upload_id",
        table_name="CONTRIBUTION_CHANGE_SET",
    )
    op.drop_index(
        "ix_contribution_change_set_state",
        table_name="CONTRIBUTION_CHANGE_SET",
    )
    op.drop_table("CONTRIBUTION_CHANGE_SET")
