"""Add durable contribution provenance.

Revision ID: 0012
Revises: 0011
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "PENDING_UPLOAD", sa.Column("submitted_by", sa.Integer(), nullable=True)
    )
    op.add_column(
        "PENDING_UPLOAD", sa.Column("base_commit", sa.String(length=64), nullable=True)
    )
    op.add_column(
        "PENDING_UPLOAD",
        sa.Column("accepted_commit", sa.String(length=64), nullable=True),
    )
    op.create_foreign_key(
        "fk_pending_upload_submitted_by_user",
        "PENDING_UPLOAD",
        "USER",
        ["submitted_by"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_PENDING_UPLOAD_submitted_by", "PENDING_UPLOAD", ["submitted_by"]
    )


def downgrade() -> None:
    op.drop_index("ix_PENDING_UPLOAD_submitted_by", table_name="PENDING_UPLOAD")
    op.drop_constraint(
        "fk_pending_upload_submitted_by_user", "PENDING_UPLOAD", type_="foreignkey"
    )
    op.drop_column("PENDING_UPLOAD", "accepted_commit")
    op.drop_column("PENDING_UPLOAD", "base_commit")
    op.drop_column("PENDING_UPLOAD", "submitted_by")
