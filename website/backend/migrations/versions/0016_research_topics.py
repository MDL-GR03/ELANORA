"""Add reusable tier-based research topics.

Revision ID: 0016
Revises: 0015
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "RESEARCH_TOPIC",
        sa.Column("topic_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "allow_new_tiers",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
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
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("topic_id"),
        sa.UniqueConstraint(
            "project_id", "name", name="uq_research_topic_project_name"
        ),
    )
    op.create_index("ix_research_topic_project", "RESEARCH_TOPIC", ["project_id"])
    op.create_table(
        "RESEARCH_TOPIC_TIER",
        sa.Column("topic_id", sa.Integer(), nullable=False),
        sa.Column("tier_name", sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(
            ["topic_id"], ["RESEARCH_TOPIC.topic_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("topic_id", "tier_name"),
    )


def downgrade() -> None:
    op.drop_table("RESEARCH_TOPIC_TIER")
    op.drop_index("ix_research_topic_project", table_name="RESEARCH_TOPIC")
    op.drop_table("RESEARCH_TOPIC")
