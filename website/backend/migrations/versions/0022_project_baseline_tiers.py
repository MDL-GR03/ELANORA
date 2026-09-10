"""Add project-wide baseline tiers for scoped research copies.

Revision ID: 0022
Revises: 0021
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: str | None = "0021"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "PROJECT_BASELINE_TIER",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("tier_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("project_id", "tier_name"),
    )


def downgrade() -> None:
    op.drop_table("PROJECT_BASELINE_TIER")
