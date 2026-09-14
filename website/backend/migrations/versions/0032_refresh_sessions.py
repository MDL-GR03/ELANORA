"""Add revocable refresh-token sessions.

Revision ID: 0032
Revises: 0031
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0032"
down_revision: str | None = "0031"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "REFRESH_SESSION",
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("rotated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["USER.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_index("ix_refresh_session_user", "REFRESH_SESSION", ["user_id"])
    op.create_index("ix_refresh_session_expiry", "REFRESH_SESSION", ["expires_at"])
    op.create_index("ix_refresh_session_revoked", "REFRESH_SESSION", ["revoked_at"])


def downgrade() -> None:
    op.drop_index("ix_refresh_session_revoked", table_name="REFRESH_SESSION")
    op.drop_index("ix_refresh_session_expiry", table_name="REFRESH_SESSION")
    op.drop_index("ix_refresh_session_user", table_name="REFRESH_SESSION")
    op.drop_table("REFRESH_SESSION")
