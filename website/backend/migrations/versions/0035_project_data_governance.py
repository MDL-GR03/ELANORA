"""Record each project's data classification, legal basis, retention and hold.

Existing projects start unclassified, without a retention period and without a
legal hold, so nothing becomes purgeable until an administrator decides.

Revision ID: 0035
Revises: 0034
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0035"
down_revision: str | None = "0034"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "PROJECT", sa.Column("data_classification", sa.String(30), nullable=True)
    )
    op.add_column("PROJECT", sa.Column("legal_basis", sa.Text(), nullable=True))
    op.add_column("PROJECT", sa.Column("retention_days", sa.Integer(), nullable=True))
    op.add_column(
        "PROJECT",
        sa.Column(
            "legal_hold", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )
    op.add_column("PROJECT", sa.Column("legal_hold_reason", sa.Text(), nullable=True))
    op.add_column(
        "PROJECT",
        sa.Column("governance_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "PROJECT",
        sa.Column("governance_updated_by", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_project_governance_updated_by",
        "PROJECT",
        "USER",
        ["governance_updated_by"],
        ["user_id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_project_data_classification",
        "PROJECT",
        "data_classification IS NULL OR data_classification IN "
        "('public', 'internal', 'confidential', 'sensitive_personal')",
    )
    op.create_check_constraint(
        "ck_project_sensitive_legal_basis",
        "PROJECT",
        "data_classification IS DISTINCT FROM 'sensitive_personal' "
        "OR btrim(coalesce(legal_basis, '')) <> ''",
    )
    op.create_check_constraint(
        "ck_project_retention_days",
        "PROJECT",
        "retention_days IS NULL OR retention_days >= 30",
    )
    op.create_check_constraint(
        "ck_project_legal_hold_reason",
        "PROJECT",
        "NOT legal_hold OR btrim(coalesce(legal_hold_reason, '')) <> ''",
    )


def downgrade() -> None:
    for name in (
        "ck_project_legal_hold_reason",
        "ck_project_retention_days",
        "ck_project_sensitive_legal_basis",
        "ck_project_data_classification",
    ):
        op.drop_constraint(name, "PROJECT", type_="check")
    op.drop_constraint(
        "fk_project_governance_updated_by", "PROJECT", type_="foreignkey"
    )
    for column in (
        "governance_updated_by",
        "governance_updated_at",
        "legal_hold_reason",
        "legal_hold",
        "retention_days",
        "legal_basis",
        "data_classification",
    ):
        op.drop_column("PROJECT", column)
