"""Make one installation equal one institution.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add stable provenance identity and enforce one institution profile."""
    op.add_column(
        "INSTANCE",
        sa.Column(
            "installation_id",
            sa.Uuid(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
    )
    op.add_column(
        "INSTANCE",
        sa.Column(
            "singleton_key",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_instance_singleton_key", "INSTANCE", "singleton_key = 1"
    )
    op.create_unique_constraint(
        "uq_instance_installation_id", "INSTANCE", ["installation_id"]
    )
    op.create_unique_constraint(
        "uq_instance_singleton_key", "INSTANCE", ["singleton_key"]
    )
    for column_name in ("created_at", "updated_at"):
        op.alter_column(
            "INSTANCE",
            column_name,
            existing_type=sa.DateTime(),
            type_=sa.DateTime(timezone=True),
            existing_nullable=False,
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )


def downgrade() -> None:
    """Restore the former multi-instance-compatible table shape."""
    for column_name in ("created_at", "updated_at"):
        op.alter_column(
            "INSTANCE",
            column_name,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(),
            existing_nullable=False,
            postgresql_using=f"{column_name} AT TIME ZONE 'UTC'",
        )
    op.drop_constraint("uq_instance_singleton_key", "INSTANCE", type_="unique")
    op.drop_constraint("uq_instance_installation_id", "INSTANCE", type_="unique")
    op.drop_constraint("ck_instance_singleton_key", "INSTANCE", type_="check")
    op.drop_column("INSTANCE", "singleton_key")
    op.drop_column("INSTANCE", "installation_id")
