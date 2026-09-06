"""retain rejected EAF ingestion attempts

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-04
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create immutable storage for rejected EAF payloads and diagnostics."""
    op.create_table(
        "EAF_INGESTION_ATTEMPT",
        sa.Column("attempt_id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("submitted_by", sa.Integer(), nullable=True),
        sa.Column("requested_project_name", sa.String(length=100), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("raw_xml", sa.LargeBinary(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("validation_issues", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("file_size >= 0", name="ck_eaf_ingestion_file_size"),
        sa.CheckConstraint("length(sha256) = 64", name="ck_eaf_ingestion_sha256"),
        sa.CheckConstraint("status = 'rejected'", name="ck_eaf_ingestion_status"),
        sa.ForeignKeyConstraint(
            ["instance_id"], ["INSTANCE.instance_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["submitted_by"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("attempt_id"),
    )
    op.create_index(
        op.f("ix_EAF_INGESTION_ATTEMPT_sha256"),
        "EAF_INGESTION_ATTEMPT",
        ["sha256"],
        unique=False,
    )


def downgrade() -> None:
    """Remove rejected-ingestion storage without touching accepted revisions."""
    op.drop_index(
        op.f("ix_EAF_INGESTION_ATTEMPT_sha256"),
        table_name="EAF_INGESTION_ATTEMPT",
    )
    op.drop_table("EAF_INGESTION_ATTEMPT")
