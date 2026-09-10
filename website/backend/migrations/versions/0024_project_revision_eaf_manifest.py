"""Attach immutable EAF manifests to accepted project revisions.

Revision ID: 0024
Revises: 0023
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "PROJECT_REVISION",
        sa.Column("manifest_sha256", sa.String(length=64), nullable=True),
    )
    op.create_check_constraint(
        "ck_project_revision_manifest_sha256",
        "PROJECT_REVISION",
        "manifest_sha256 IS NULL OR length(manifest_sha256) = 64",
    )
    op.create_table(
        "PROJECT_REVISION_EAF",
        sa.Column("project_revision_id", sa.Uuid(), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("eaf_revision_id", sa.Uuid(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "length(sha256) = 64", name="ck_project_revision_eaf_sha256"
        ),
        sa.ForeignKeyConstraint(
            ["eaf_revision_id"], ["EAF_REVISION.revision_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["project_revision_id"],
            ["PROJECT_REVISION.revision_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_revision_id", "filename"),
    )
    op.create_index(
        "ix_PROJECT_REVISION_EAF_eaf_revision_id",
        "PROJECT_REVISION_EAF",
        ["eaf_revision_id"],
        unique=False,
    )
    op.execute(
        """
        CREATE FUNCTION prevent_project_revision_eaf_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'PROJECT_REVISION_EAF is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER project_revision_eaf_no_update_or_delete
        BEFORE UPDATE OR DELETE ON "PROJECT_REVISION_EAF"
        FOR EACH ROW EXECUTE FUNCTION prevent_project_revision_eaf_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER project_revision_eaf_no_update_or_delete "
        'ON "PROJECT_REVISION_EAF"'
    )
    op.execute("DROP FUNCTION prevent_project_revision_eaf_mutation()")
    op.drop_index(
        "ix_PROJECT_REVISION_EAF_eaf_revision_id",
        table_name="PROJECT_REVISION_EAF",
    )
    op.drop_table("PROJECT_REVISION_EAF")
    op.drop_constraint(
        "ck_project_revision_manifest_sha256",
        "PROJECT_REVISION",
        type_="check",
    )
    op.drop_column("PROJECT_REVISION", "manifest_sha256")
