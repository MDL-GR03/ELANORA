"""Add non-destructive published protocol archives.

Revision ID: 0014
Revises: 0013
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "PROTOCOL_VERSION_ARCHIVE",
        sa.Column("protocol_version_id", sa.Uuid(), nullable=False),
        sa.Column("archived_by", sa.Integer(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["protocol_version_id"],
            ["PROTOCOL_VERSION.protocol_version_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["archived_by"], ["USER.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("protocol_version_id"),
    )


def downgrade() -> None:
    op.drop_table("PROTOCOL_VERSION_ARCHIVE")
