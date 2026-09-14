"""Enforce workflow state, timestamp, and result consistency.

Revision ID: 0031
Revises: 0030
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0031"
down_revision: str | None = "0030"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    invalid = (
        op.get_bind()
        .execute(
            sa.text(
                """
                SELECT record_type, record_id
                FROM (
                    SELECT 'pending upload' AS record_type,
                           upload_id::text AS record_id
                    FROM "PENDING_UPLOAD"
                    WHERE NOT (
                        (status IN ('RESOLVED', 'NO_CHANGES', 'DISMISSED')
                         AND resolved_at IS NOT NULL)
                        OR
                        (status NOT IN ('RESOLVED', 'NO_CHANGES', 'DISMISSED')
                         AND resolved_at IS NULL)
                    )

                    UNION ALL

                    SELECT 'contribution change set', change_set_id::text
                    FROM "CONTRIBUTION_CHANGE_SET"
                    WHERE attempts < 0
                       OR NOT (
                           (state = 'completed' AND completed_at IS NOT NULL
                            AND resulting_commit IS NOT NULL)
                           OR
                           (state <> 'completed' AND completed_at IS NULL)
                       )

                    UNION ALL

                    SELECT 'project sync operation', operation_id::text
                    FROM "PROJECT_SYNC_OPERATION"
                    WHERE NOT (
                        (state IN ('completed', 'discarded')
                         AND completed_at IS NOT NULL)
                        OR
                        (state NOT IN ('completed', 'discarded')
                         AND completed_at IS NULL)
                    )
                       OR (state = 'completed' AND resulting_commit IS NULL)

                    UNION ALL

                    SELECT 'review case', case_id::text
                    FROM "REVIEW_CASE"
                    WHERE NOT (
                        (state IN ('resolved', 'closed')
                         AND resolved_at IS NOT NULL)
                        OR
                        (state NOT IN ('resolved', 'closed')
                         AND resolved_at IS NULL)
                    )

                    UNION ALL

                    SELECT 'project compliance scan', scan_id::text
                    FROM "PROJECT_COMPLIANCE_SCAN"
                    WHERE total_files < 0 OR passed_files < 0 OR failed_files < 0
                       OR passed_files + failed_files > total_files
                       OR (status = 'running' AND completed_at IS NOT NULL)
                       OR (status = 'completed' AND completed_at IS NULL)
                ) AS invalid_workflows
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if invalid is not None:
        raise RuntimeError(
            "Migration 0031 cannot enforce workflow lifecycle consistency: "
            f"{invalid['record_type']} {invalid['record_id']} has contradictory "
            "state, timestamp, result, or count data. Repair that record, then "
            "rerun the migration."
        )

    op.create_check_constraint(
        "ck_pending_upload_resolution_lifecycle",
        "PENDING_UPLOAD",
        "(status IN ('RESOLVED', 'NO_CHANGES', 'DISMISSED') "
        "AND resolved_at IS NOT NULL) OR "
        "(status NOT IN ('RESOLVED', 'NO_CHANGES', 'DISMISSED') "
        "AND resolved_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_contribution_change_set_attempts_nonnegative",
        "CONTRIBUTION_CHANGE_SET",
        "attempts >= 0",
    )
    op.create_check_constraint(
        "ck_contribution_change_set_completion",
        "CONTRIBUTION_CHANGE_SET",
        "(state = 'completed' AND completed_at IS NOT NULL "
        "AND resulting_commit IS NOT NULL) OR "
        "(state <> 'completed' AND completed_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_project_sync_operation_completion",
        "PROJECT_SYNC_OPERATION",
        "(state IN ('completed','discarded') AND completed_at IS NOT NULL) OR "
        "(state NOT IN ('completed','discarded') AND completed_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_project_sync_operation_completed_commit",
        "PROJECT_SYNC_OPERATION",
        "state <> 'completed' OR resulting_commit IS NOT NULL",
    )
    op.create_check_constraint(
        "ck_review_case_resolution_lifecycle",
        "REVIEW_CASE",
        "(state IN ('resolved','closed') AND resolved_at IS NOT NULL) OR "
        "(state NOT IN ('resolved','closed') AND resolved_at IS NULL)",
    )
    op.create_check_constraint(
        "ck_compliance_scan_counts_nonnegative",
        "PROJECT_COMPLIANCE_SCAN",
        "total_files >= 0 AND passed_files >= 0 AND failed_files >= 0",
    )
    op.create_check_constraint(
        "ck_compliance_scan_counts_within_total",
        "PROJECT_COMPLIANCE_SCAN",
        "passed_files + failed_files <= total_files",
    )
    op.create_check_constraint(
        "ck_compliance_scan_running_incomplete",
        "PROJECT_COMPLIANCE_SCAN",
        "status <> 'running' OR completed_at IS NULL",
    )
    op.create_check_constraint(
        "ck_compliance_scan_completed_at",
        "PROJECT_COMPLIANCE_SCAN",
        "status <> 'completed' OR completed_at IS NOT NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_compliance_scan_completed_at", "PROJECT_COMPLIANCE_SCAN", type_="check"
    )
    op.drop_constraint(
        "ck_compliance_scan_running_incomplete",
        "PROJECT_COMPLIANCE_SCAN",
        type_="check",
    )
    op.drop_constraint(
        "ck_compliance_scan_counts_within_total",
        "PROJECT_COMPLIANCE_SCAN",
        type_="check",
    )
    op.drop_constraint(
        "ck_compliance_scan_counts_nonnegative",
        "PROJECT_COMPLIANCE_SCAN",
        type_="check",
    )
    op.drop_constraint(
        "ck_review_case_resolution_lifecycle", "REVIEW_CASE", type_="check"
    )
    op.drop_constraint(
        "ck_project_sync_operation_completed_commit",
        "PROJECT_SYNC_OPERATION",
        type_="check",
    )
    op.drop_constraint(
        "ck_project_sync_operation_completion",
        "PROJECT_SYNC_OPERATION",
        type_="check",
    )
    op.drop_constraint(
        "ck_contribution_change_set_completion",
        "CONTRIBUTION_CHANGE_SET",
        type_="check",
    )
    op.drop_constraint(
        "ck_contribution_change_set_attempts_nonnegative",
        "CONTRIBUTION_CHANGE_SET",
        type_="check",
    )
    op.drop_constraint(
        "ck_pending_upload_resolution_lifecycle", "PENDING_UPLOAD", type_="check"
    )
