"""Add institution-controlled instance branding.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add validated hexadecimal theme colors to the institution profile."""
    for name, default in (
        ("primary_color", "#2563eb"),
        ("secondary_color", "#0f766e"),
        ("accent_color", "#d97706"),
    ):
        op.add_column(
            "INSTANCE",
            sa.Column(
                name, sa.String(length=7), server_default=default, nullable=False
            ),
        )
        op.create_check_constraint(
            f"ck_instance_{name}_hex",
            "INSTANCE",
            f"{name} ~ '^#[0-9A-Fa-f]{{6}}$'",
        )


def downgrade() -> None:
    """Remove instance theme colors."""
    for name in ("accent_color", "secondary_color", "primary_color"):
        op.drop_constraint(f"ck_instance_{name}_hex", "INSTANCE", type_="check")
        op.drop_column("INSTANCE", name)
