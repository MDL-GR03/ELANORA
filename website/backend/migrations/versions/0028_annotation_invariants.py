"""Enforce annotation time validity and tier ownership.

Revision ID: 0028
Revises: 0027
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: str | None = "0027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    invalid = (
        connection.execute(
            sa.text(
                """
            SELECT annotation_id, elan_id, tier_id, start_time, end_time
              FROM "ANNOTATION" AS annotation
             WHERE start_time < 0
                OR end_time < 0
                OR (start_time IS NOT NULL AND end_time IS NOT NULL
                    AND end_time < start_time)
                OR NOT EXISTS (
                    SELECT 1
                      FROM "TIER" AS tier
                     WHERE tier.tier_id = annotation.tier_id
                       AND tier.elan_id = annotation.elan_id
                )
             LIMIT 1
            """
            )
        )
        .mappings()
        .first()
    )
    if invalid is not None:
        raise RuntimeError(
            "Migration 0028 cannot enforce annotation invariants: "
            f"annotation {invalid['annotation_id']!r} in ELAN file "
            f"{invalid['elan_id']} has an invalid time range or tier ownership. "
            "Repair or remove the invalid derived projection, then rerun the migration."
        )

    op.create_check_constraint(
        "ck_annotation_start_time_nonnegative",
        "ANNOTATION",
        "start_time IS NULL OR start_time >= 0",
    )
    op.create_check_constraint(
        "ck_annotation_end_time_nonnegative",
        "ANNOTATION",
        "end_time IS NULL OR end_time >= 0",
    )
    op.create_check_constraint(
        "ck_annotation_time_interval",
        "ANNOTATION",
        "start_time IS NULL OR end_time IS NULL OR end_time >= start_time",
    )
    op.create_unique_constraint("uq_tier_identity_elan", "TIER", ["tier_id", "elan_id"])
    op.drop_constraint("ANNOTATION_tier_id_fkey", "ANNOTATION", type_="foreignkey")
    op.create_foreign_key(
        "fk_annotation_tier_elan",
        "ANNOTATION",
        "TIER",
        ["tier_id", "elan_id"],
        ["tier_id", "elan_id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_annotation_tier_elan", "ANNOTATION", type_="foreignkey")
    op.create_foreign_key(
        "ANNOTATION_tier_id_fkey",
        "ANNOTATION",
        "TIER",
        ["tier_id"],
        ["tier_id"],
    )
    op.drop_constraint("uq_tier_identity_elan", "TIER", type_="unique")
    op.drop_constraint("ck_annotation_time_interval", "ANNOTATION", type_="check")
    op.drop_constraint(
        "ck_annotation_end_time_nonnegative", "ANNOTATION", type_="check"
    )
    op.drop_constraint(
        "ck_annotation_start_time_nonnegative", "ANNOTATION", type_="check"
    )
