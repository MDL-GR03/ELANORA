"""Add contribution version lineage.

Revision ID: 0019
Revises: 0018
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "PENDING_UPLOAD",
        sa.Column("superseded_by_upload_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_pending_upload_superseded_by",
        "PENDING_UPLOAD",
        "PENDING_UPLOAD",
        ["superseded_by_upload_id"],
        ["upload_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        "ix_PENDING_UPLOAD_superseded_by_upload_id",
        "PENDING_UPLOAD",
        ["superseded_by_upload_id"],
    )
    op.execute(
        'UPDATE "PENDING_UPLOAD" AS original '
        "SET superseded_by_upload_id = review.resubmitted_upload_id "
        'FROM "REVIEW_CASE" AS review '
        "WHERE review.upload_id = original.upload_id "
        "AND review.resubmitted_upload_id IS NOT NULL"
    )


def downgrade() -> None:
    op.drop_index(
        "ix_PENDING_UPLOAD_superseded_by_upload_id", table_name="PENDING_UPLOAD"
    )
    op.drop_constraint(
        "fk_pending_upload_superseded_by", "PENDING_UPLOAD", type_="foreignkey"
    )
    op.drop_column("PENDING_UPLOAD", "superseded_by_upload_id")
