"""allow projects without a description

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Allow the optional description already accepted by project creation."""
    op.alter_column("PROJECT", "description", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    """Restore the original requirement after replacing nulls safely."""
    op.execute("UPDATE \"PROJECT\" SET description = '' WHERE description IS NULL")
    op.alter_column("PROJECT", "description", existing_type=sa.Text(), nullable=False)
