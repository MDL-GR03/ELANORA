"""Add durable institution logo metadata.

Revision ID: 0008
Revises: 0007
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "INSTANCE_ASSET",
        sa.Column("asset_id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("storage_key", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["instance_id"], ["INSTANCE.instance_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by"], ["USER.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("asset_id"),
        sa.UniqueConstraint("storage_key"),
        sa.CheckConstraint("kind = 'logo'", name="ck_instance_asset_kind"),
        sa.CheckConstraint(
            "byte_size > 0 AND width > 0 AND height > 0",
            name="ck_instance_asset_dimensions",
        ),
        sa.CheckConstraint("length(sha256) = 64", name="ck_instance_asset_sha256"),
    )
    op.add_column("INSTANCE", sa.Column("logo_asset_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_instance_logo_asset",
        "INSTANCE",
        "INSTANCE_ASSET",
        ["logo_asset_id"],
        ["asset_id"],
        ondelete="SET NULL",
        use_alter=True,
    )


def downgrade() -> None:
    op.drop_constraint("fk_instance_logo_asset", "INSTANCE", type_="foreignkey")
    op.drop_column("INSTANCE", "logo_asset_id")
    op.drop_table("INSTANCE_ASSET")
