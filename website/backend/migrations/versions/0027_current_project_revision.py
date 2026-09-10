"""Make the published project revision explicit.

Revision ID: 0027
Revises: 0026
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: str | None = "0026"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("PROJECT", sa.Column("current_revision_id", sa.Uuid(), nullable=True))
    op.create_unique_constraint(
        "uq_project_revision_identity_project",
        "PROJECT_REVISION",
        ["revision_id", "project_id"],
    )
    op.create_foreign_key(
        "fk_project_current_revision",
        "PROJECT",
        "PROJECT_REVISION",
        ["current_revision_id", "project_id"],
        ["revision_id", "project_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_PROJECT_current_revision_id"),
        "PROJECT",
        ["current_revision_id"],
        unique=False,
    )
    op.execute(
        sa.text(
            """
            UPDATE "PROJECT" AS project
               SET current_revision_id = latest.revision_id
              FROM (
                    SELECT DISTINCT ON (project_id) project_id, revision_id
                      FROM "PROJECT_REVISION"
                     WHERE manifest_sha256 IS NOT NULL
                     ORDER BY project_id, ordinal DESC
                   ) AS latest
             WHERE latest.project_id = project.project_id
            """
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_PROJECT_current_revision_id"), table_name="PROJECT")
    op.drop_constraint("fk_project_current_revision", "PROJECT", type_="foreignkey")
    op.drop_column("PROJECT", "current_revision_id")
    op.drop_constraint(
        "uq_project_revision_identity_project", "PROJECT_REVISION", type_="unique"
    )
