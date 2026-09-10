"""Turn legacy single-file correction targets into explicit review tasks.

Revision ID: 0020
Revises: 0019
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO "REVIEW_TASK" (
            task_id, case_id, filename, instruction, tier_id, annotation_id,
            start_ms, end_ms, current_text, suggested_text, status, created_at
        )
        SELECT
            (md5(rc.case_id::text || '-legacy-file-task'))::uuid,
            rc.case_id,
            rc.filename,
            COALESCE(
                NULLIF(rc.suggested_text, ''),
                NULLIF(comment.body, ''),
                'Review and correct the requested file.'
            ),
            rc.tier_id,
            rc.annotation_id,
            rc.start_ms,
            rc.end_ms,
            rc.current_text,
            rc.suggested_text,
            'requested',
            rc.created_at
        FROM "REVIEW_CASE" AS rc
        LEFT JOIN LATERAL (
            SELECT body
            FROM "REVIEW_COMMENT"
            WHERE case_id = rc.case_id
            ORDER BY created_at ASC
            LIMIT 1
        ) AS comment ON true
        WHERE rc.filename IS NOT NULL
          AND NOT EXISTS (
              SELECT 1 FROM "REVIEW_TASK" AS task
              WHERE task.case_id = rc.case_id
          )
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM "REVIEW_TASK" AS task
        USING "REVIEW_CASE" AS rc
        WHERE task.case_id = rc.case_id
          AND task.task_id = (md5(rc.case_id::text || '-legacy-file-task'))::uuid
        """
    )
