"""Enforce project ownership across contribution and revision links.

Revision ID: 0029
Revises: 0028
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: str | None = "0028"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid = (
        connection.execute(
            sa.text(
                """
                SELECT link_type, record_id, project_id, linked_project_id
                FROM (
                    SELECT
                        'contribution change set' AS link_type,
                        change_set_id::text AS record_id,
                        change_set.project_id,
                        upload.project_id AS linked_project_id
                    FROM "CONTRIBUTION_CHANGE_SET" AS change_set
                    JOIN "PENDING_UPLOAD" AS upload
                      ON upload.upload_id = change_set.upload_id
                    WHERE upload.project_id <> change_set.project_id

                    UNION ALL

                    SELECT
                        'review case upload', review.case_id::text,
                        review.project_id, upload.project_id
                    FROM "REVIEW_CASE" AS review
                    JOIN "PENDING_UPLOAD" AS upload
                      ON upload.upload_id = review.upload_id
                    WHERE upload.project_id <> review.project_id

                    UNION ALL

                    SELECT
                        'review case resubmission', review.case_id::text,
                        review.project_id, upload.project_id
                    FROM "REVIEW_CASE" AS review
                    JOIN "PENDING_UPLOAD" AS upload
                      ON upload.upload_id = review.resubmitted_upload_id
                    WHERE upload.project_id <> review.project_id

                    UNION ALL

                    SELECT
                        'project revision contribution', revision.revision_id::text,
                        revision.project_id, upload.project_id
                    FROM "PROJECT_REVISION" AS revision
                    JOIN "PENDING_UPLOAD" AS upload
                      ON upload.upload_id = revision.contribution_id
                    WHERE upload.project_id <> revision.project_id

                    UNION ALL

                    SELECT
                        'project integrity revision', integrity.project_id::text,
                        integrity.project_id, revision.project_id
                    FROM "PROJECT_INTEGRITY_STATUS" AS integrity
                    JOIN "PROJECT_REVISION" AS revision
                      ON revision.revision_id = integrity.revision_id
                    WHERE revision.project_id <> integrity.project_id
                ) AS invalid_links
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if invalid is not None:
        raise RuntimeError(
            "Migration 0029 cannot enforce project ownership: "
            f"{invalid['link_type']} record {invalid['record_id']} belongs to "
            f"project {invalid['project_id']} but its linked record belongs to "
            f"project {invalid['linked_project_id']}. Repair the invalid link, "
            "then rerun the migration."
        )

    op.create_unique_constraint(
        "uq_pending_upload_identity_project",
        "PENDING_UPLOAD",
        ["upload_id", "project_id"],
    )

    op.drop_constraint(
        "CONTRIBUTION_CHANGE_SET_upload_id_fkey",
        "CONTRIBUTION_CHANGE_SET",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_contribution_change_set_upload_project",
        "CONTRIBUTION_CHANGE_SET",
        "PENDING_UPLOAD",
        ["upload_id", "project_id"],
        ["upload_id", "project_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint("REVIEW_CASE_upload_id_fkey", "REVIEW_CASE", type_="foreignkey")
    op.drop_constraint(
        "REVIEW_CASE_resubmitted_upload_id_fkey",
        "REVIEW_CASE",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_review_case_upload_project",
        "REVIEW_CASE",
        "PENDING_UPLOAD",
        ["upload_id", "project_id"],
        ["upload_id", "project_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_review_case_resubmission_project",
        "REVIEW_CASE",
        "PENDING_UPLOAD",
        ["resubmitted_upload_id", "project_id"],
        ["upload_id", "project_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "PROJECT_REVISION_contribution_id_fkey",
        "PROJECT_REVISION",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_project_revision_contribution_project",
        "PROJECT_REVISION",
        "PENDING_UPLOAD",
        ["contribution_id", "project_id"],
        ["upload_id", "project_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "PROJECT_INTEGRITY_STATUS_revision_id_fkey",
        "PROJECT_INTEGRITY_STATUS",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_project_integrity_revision_project",
        "PROJECT_INTEGRITY_STATUS",
        "PROJECT_REVISION",
        ["revision_id", "project_id"],
        ["revision_id", "project_id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_project_integrity_revision_project",
        "PROJECT_INTEGRITY_STATUS",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "PROJECT_INTEGRITY_STATUS_revision_id_fkey",
        "PROJECT_INTEGRITY_STATUS",
        "PROJECT_REVISION",
        ["revision_id"],
        ["revision_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_project_revision_contribution_project",
        "PROJECT_REVISION",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "PROJECT_REVISION_contribution_id_fkey",
        "PROJECT_REVISION",
        "PENDING_UPLOAD",
        ["contribution_id"],
        ["upload_id"],
        ondelete="SET NULL",
    )

    op.drop_constraint(
        "fk_review_case_resubmission_project", "REVIEW_CASE", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_review_case_upload_project", "REVIEW_CASE", type_="foreignkey"
    )
    op.create_foreign_key(
        "REVIEW_CASE_resubmitted_upload_id_fkey",
        "REVIEW_CASE",
        "PENDING_UPLOAD",
        ["resubmitted_upload_id"],
        ["upload_id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "REVIEW_CASE_upload_id_fkey",
        "REVIEW_CASE",
        "PENDING_UPLOAD",
        ["upload_id"],
        ["upload_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "fk_contribution_change_set_upload_project",
        "CONTRIBUTION_CHANGE_SET",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "CONTRIBUTION_CHANGE_SET_upload_id_fkey",
        "CONTRIBUTION_CHANGE_SET",
        "PENDING_UPLOAD",
        ["upload_id"],
        ["upload_id"],
        ondelete="RESTRICT",
    )

    op.drop_constraint(
        "uq_pending_upload_identity_project", "PENDING_UPLOAD", type_="unique"
    )
