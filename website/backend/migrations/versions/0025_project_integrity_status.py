"""Persist accepted project integrity incidents.

Revision ID: 0025
Revises: 0024
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0025"
down_revision: str | None = "0024"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "PROJECT_INTEGRITY_STATUS",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("first_detected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["PROJECT_REVISION.revision_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("project_id"),
    )
    op.create_index(
        "ix_PROJECT_INTEGRITY_STATUS_status",
        "PROJECT_INTEGRITY_STATUS",
        ["status"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_PROJECT_INTEGRITY_STATUS_status",
        table_name="PROJECT_INTEGRITY_STATUS",
    )
    op.drop_table("PROJECT_INTEGRITY_STATUS")
