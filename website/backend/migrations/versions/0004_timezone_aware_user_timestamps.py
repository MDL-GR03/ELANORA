"""Store user timestamps as timezone-aware UTC values.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Interpret existing naive values as UTC and enable timezone storage."""
    for column_name, nullable in (
        ("created_at", False),
        ("updated_at", False),
        ("last_login", True),
    ):
        op.alter_column(
            "USER",
            column_name,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Convert UTC instants back to naive UTC timestamps."""
    for column_name, nullable in (
        ("created_at", False),
        ("updated_at", False),
        ("last_login", True),
    ):
        op.alter_column(
            "USER",
            column_name,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=nullable,
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )
