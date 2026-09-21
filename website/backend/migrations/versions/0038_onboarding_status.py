"""Add onboarding status tracking for new installations.

This migration adds the onboarding_status table to track the progress of new
installations through the guided setup workflow. It allows administrators
to be guided through creating their first project, configuring protocols,
inviting their first collaborator, and uploading their first files.

Revision ID: 0038
Revises: 0037
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0038"
down_revision: str | None = "0037"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the onboarding_status table."""
    op.create_table(
        "onboarding_status",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column(
            "current_step",
            sa.Enum(
                "not_started",
                "project_created",
                "protocol_configured",
                "collaborator_invited",
                "first_upload",
                "complete",
                "skipped",
                name="onboardingstep",
            ),
            nullable=False,
        ),
        sa.Column("project_created", sa.Boolean(), nullable=False, default=False),
        sa.Column("protocol_configured", sa.Boolean(), nullable=False, default=False),
        sa.Column("collaborator_invited", sa.Boolean(), nullable=False, default=False),
        sa.Column("first_upload", sa.Boolean(), nullable=False, default=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("instance_id", name="uq_onboarding_status_instance_id"),
        sa.ForeignKeyConstraint(
            ["instance_id"],
            ["INSTANCE.instance_id"],
            name="fk_onboarding_status_instance_id",
            ondelete="CASCADE",
        ),
    )


def downgrade() -> None:
    """Drop the onboarding_status table and its enum type."""
    op.drop_table("onboarding_status")
    op.execute("DROP TYPE IF EXISTS onboardingstep CASCADE")
