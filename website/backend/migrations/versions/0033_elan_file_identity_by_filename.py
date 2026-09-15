"""Identify a projected EAF by its filename within a project, not its bytes.

The inherited uq_content_project constraint made (content_id, project_id)
unique. Because file content is deduplicated by hash, two distinct files with
identical bytes, such as sessions started from one template, could never both
be projected, and publishing the second one always failed. What identifies a
file in a project is its name, which is also how revision manifests key it.

Revision ID: 0033
Revises: 0032
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0033"
down_revision: str | None = "0032"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    duplicate = (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT project_id, filename
                FROM "ELAN_FILE"
                GROUP BY project_id, filename
                HAVING count(*) > 1
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if duplicate is not None:
        raise RuntimeError(
            "Migration 0033 cannot make EAF filenames unique within a project: "
            f"project {duplicate['project_id']} projects '{duplicate['filename']}' "
            "more than once. Remove the stale projection row, then rerun the "
            "migration."
        )

    op.drop_constraint("uq_content_project", "ELAN_FILE", type_="unique")
    op.create_unique_constraint(
        "uq_elan_file_project_filename", "ELAN_FILE", ["project_id", "filename"]
    )


def downgrade() -> None:
    shared = (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT project_id, content_id
                FROM "ELAN_FILE"
                GROUP BY project_id, content_id
                HAVING count(*) > 1
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if shared is not None:
        raise RuntimeError(
            "Migration 0033 cannot be downgraded: project "
            f"{shared['project_id']} holds several files with identical content "
            f"{shared['content_id']}, which the previous schema cannot represent."
        )

    op.drop_constraint("uq_elan_file_project_filename", "ELAN_FILE", type_="unique")
    op.create_unique_constraint(
        "uq_content_project", "ELAN_FILE", ["content_id", "project_id"]
    )
