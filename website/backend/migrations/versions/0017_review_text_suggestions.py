"""Add structured text suggestions to review cases.

Revision ID: 0017
Revises: 0016
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("REVIEW_CASE", sa.Column("current_text", sa.Text(), nullable=True))
    op.add_column("REVIEW_CASE", sa.Column("suggested_text", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("REVIEW_CASE", "suggested_text")
    op.drop_column("REVIEW_CASE", "current_text")
