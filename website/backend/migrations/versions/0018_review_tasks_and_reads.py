"""Add grouped file tasks and review read receipts.

Revision ID: 0018
Revises: 0017
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "REVIEW_TASK",
        sa.Column("task_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("tier_id", sa.String(255), nullable=True),
        sa.Column("annotation_id", sa.String(255), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("current_text", sa.Text(), nullable=True),
        sa.Column("suggested_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(24), server_default="requested", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "status IN ('requested','addressed','accepted','reopened')",
            name="ck_review_task_status",
        ),
        sa.CheckConstraint(
            "start_ms IS NULL OR start_ms >= 0", name="ck_review_task_start"
        ),
        sa.CheckConstraint(
            "end_ms IS NULL OR end_ms >= start_ms", name="ck_review_task_interval"
        ),
        sa.ForeignKeyConstraint(
            ["case_id"], ["REVIEW_CASE.case_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("task_id"),
    )
    op.create_index("ix_REVIEW_TASK_case_id", "REVIEW_TASK", ["case_id"])
    op.create_table(
        "REVIEW_CASE_VIEW",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["REVIEW_CASE.case_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["USER.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("case_id", "user_id"),
    )


def downgrade() -> None:
    op.drop_table("REVIEW_CASE_VIEW")
    op.drop_index("ix_REVIEW_TASK_case_id", table_name="REVIEW_TASK")
    op.drop_table("REVIEW_TASK")
