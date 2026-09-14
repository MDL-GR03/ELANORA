"""Enforce nonblank and normalized research topic identifiers.

Revision ID: 0030
Revises: 0029
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0030"
down_revision: str | None = "0029"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    connection = op.get_bind()
    blank = (
        connection.execute(
            sa.text(
                """
                SELECT record_type, record_id
                FROM (
                    SELECT 'research topic' AS record_type, topic_id::text AS record_id
                    FROM "RESEARCH_TOPIC"
                    WHERE btrim(name) = ''

                    UNION ALL

                    SELECT 'research topic tier', topic_id::text || ':' || tier_name
                    FROM "RESEARCH_TOPIC_TIER"
                    WHERE btrim(tier_name) = ''

                    UNION ALL

                    SELECT 'project baseline tier', project_id::text || ':' || tier_name
                    FROM "PROJECT_BASELINE_TIER"
                    WHERE btrim(tier_name) = ''
                ) AS blank_identifiers
                LIMIT 1
                """
            )
        )
        .mappings()
        .first()
    )
    if blank is not None:
        raise RuntimeError(
            "Migration 0030 cannot enforce nonblank topic identifiers: "
            f"{blank['record_type']} {blank['record_id']!r} is blank. Rename or "
            "remove that identifier, then rerun the migration."
        )

    duplicate = (
        connection.execute(
            sa.text(
                """
                SELECT project_id,
                       lower(regexp_replace(btrim(name), '\\s+', ' ', 'g'))
                           AS normalized_name,
                       array_agg(name ORDER BY topic_id) AS names
                FROM "RESEARCH_TOPIC"
                GROUP BY project_id,
                         lower(regexp_replace(btrim(name), '\\s+', ' ', 'g'))
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
            "Migration 0030 cannot enforce normalized topic identity: project "
            f"{duplicate['project_id']} contains equivalent topic names "
            f"{duplicate['names']}. Merge or rename them explicitly, then rerun "
            "the migration."
        )

    op.create_check_constraint(
        "ck_research_topic_name_nonblank", "RESEARCH_TOPIC", "btrim(name) <> ''"
    )
    op.create_check_constraint(
        "ck_research_topic_tier_name_nonblank",
        "RESEARCH_TOPIC_TIER",
        "btrim(tier_name) <> ''",
    )
    op.create_check_constraint(
        "ck_project_baseline_tier_name_nonblank",
        "PROJECT_BASELINE_TIER",
        "btrim(tier_name) <> ''",
    )
    op.create_index(
        "uq_research_topic_project_normalized_name",
        "RESEARCH_TOPIC",
        [
            "project_id",
            sa.text("lower(regexp_replace(btrim(name), '\\s+', ' ', 'g'))"),
        ],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "uq_research_topic_project_normalized_name", table_name="RESEARCH_TOPIC"
    )
    op.drop_constraint(
        "ck_project_baseline_tier_name_nonblank",
        "PROJECT_BASELINE_TIER",
        type_="check",
    )
    op.drop_constraint(
        "ck_research_topic_tier_name_nonblank",
        "RESEARCH_TOPIC_TIER",
        type_="check",
    )
    op.drop_constraint(
        "ck_research_topic_name_nonblank", "RESEARCH_TOPIC", type_="check"
    )
