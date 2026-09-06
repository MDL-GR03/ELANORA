"""Add immutable protocol governance and validation evidence.

Revision ID: 0006
Revises: 0005
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create protocol, capability and immutable validation tables."""
    op.create_table(
        "PROTOCOL",
        sa.Column("protocol_id", sa.Uuid(), nullable=False),
        sa.Column("instance_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["USER.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["instance_id"], ["INSTANCE.instance_id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("protocol_id"),
        sa.UniqueConstraint("instance_id", "name", name="uq_protocol_instance_name"),
    )
    op.create_table(
        "PROTOCOL_VERSION",
        sa.Column("protocol_version_id", sa.Uuid(), nullable=False),
        sa.Column("protocol_id", sa.Uuid(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("rules", sa.JSON(), nullable=False),
        sa.Column("rules_sha256", sa.String(length=64), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("published_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("version_number > 0", name="ck_protocol_version_positive"),
        sa.CheckConstraint(
            "status IN ('draft', 'published')", name="ck_protocol_version_status"
        ),
        sa.CheckConstraint(
            "rules_sha256 IS NULL OR length(rules_sha256) = 64",
            name="ck_protocol_version_sha256",
        ),
        sa.CheckConstraint(
            "(status = 'draft' AND rules_sha256 IS NULL "
            "AND published_by IS NULL AND published_at IS NULL) OR "
            "(status = 'published' AND rules_sha256 IS NOT NULL "
            "AND published_by IS NOT NULL AND published_at IS NOT NULL)",
            name="ck_protocol_version_lifecycle",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["USER.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["protocol_id"], ["PROTOCOL.protocol_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["published_by"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("protocol_version_id"),
        sa.UniqueConstraint(
            "protocol_id", "version_number", name="uq_protocol_version_number"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_published_protocol_version_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'published' THEN
                RAISE EXCEPTION 'published protocol versions are immutable';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER protocol_version_immutable
        BEFORE UPDATE OR DELETE ON "PROTOCOL_VERSION"
        FOR EACH ROW EXECUTE FUNCTION prevent_published_protocol_version_mutation()
        """
    )
    op.add_column("PROJECT", sa.Column("protocol_version_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_project_protocol_version",
        "PROJECT",
        "PROTOCOL_VERSION",
        ["protocol_version_id"],
        ["protocol_version_id"],
        ondelete="RESTRICT",
    )
    op.create_index(
        op.f("ix_PROJECT_protocol_version_id"),
        "PROJECT",
        ["protocol_version_id"],
        unique=False,
    )
    op.create_table(
        "PROJECT_CAPABILITY_GRANT",
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("capability", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["project_id", "user_id"],
            ["USER_TO_PROJECT.project_id", "USER_TO_PROJECT.user_id"],
            name="fk_capability_project_membership",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "user_id", "capability"),
    )
    op.create_table(
        "VALIDATOR_RELEASE",
        sa.Column("validator_release_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("version", sa.String(length=50), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "length(checksum_sha256) = 64", name="ck_validator_checksum"
        ),
        sa.PrimaryKeyConstraint("validator_release_id"),
        sa.UniqueConstraint(
            "name", "version", name="uq_validator_release_name_version"
        ),
    )
    op.create_table(
        "VALIDATION_RUN",
        sa.Column("validation_run_id", sa.Uuid(), nullable=False),
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("protocol_version_id", sa.Uuid(), nullable=False),
        sa.Column("validator_release_id", sa.Uuid(), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "outcome IN ('passed', 'failed')", name="ck_validation_run_outcome"
        ),
        sa.ForeignKeyConstraint(
            ["protocol_version_id"],
            ["PROTOCOL_VERSION.protocol_version_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["revision_id"], ["EAF_REVISION.revision_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["validator_release_id"],
            ["VALIDATOR_RELEASE.validator_release_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("validation_run_id"),
        sa.UniqueConstraint(
            "revision_id",
            "protocol_version_id",
            "validator_release_id",
            name="uq_validation_run_inputs",
        ),
    )
    op.create_table(
        "VALIDATION_ISSUE",
        sa.Column("validation_issue_id", sa.Uuid(), nullable=False),
        sa.Column("validation_run_id", sa.Uuid(), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("location", sa.String(length=1000), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("rule_key", sa.String(length=200), nullable=True),
        sa.CheckConstraint("issue_number > 0", name="ck_validation_issue_positive"),
        sa.CheckConstraint(
            "severity IN ('error', 'warning')", name="ck_validation_issue_severity"
        ),
        sa.ForeignKeyConstraint(
            ["validation_run_id"],
            ["VALIDATION_RUN.validation_run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("validation_issue_id"),
        sa.UniqueConstraint(
            "validation_run_id", "issue_number", name="uq_validation_issue_number"
        ),
    )
    op.execute(
        """
        CREATE FUNCTION prevent_immutable_validation_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'validation evidence is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    for table_name in ("VALIDATOR_RELEASE", "VALIDATION_RUN", "VALIDATION_ISSUE"):
        op.execute(
            f"""
            CREATE TRIGGER validation_evidence_immutable
            BEFORE UPDATE OR DELETE ON "{table_name}"
            FOR EACH ROW EXECUTE FUNCTION
                prevent_immutable_validation_evidence_mutation()
            """
        )


def downgrade() -> None:
    """Remove protocol governance in dependency-safe order."""
    for table_name in ("VALIDATION_ISSUE", "VALIDATION_RUN", "VALIDATOR_RELEASE"):
        op.execute(f'DROP TRIGGER validation_evidence_immutable ON "{table_name}"')
    op.execute("DROP FUNCTION prevent_immutable_validation_evidence_mutation()")
    op.drop_table("VALIDATION_ISSUE")
    op.drop_table("VALIDATION_RUN")
    op.drop_table("VALIDATOR_RELEASE")
    op.drop_table("PROJECT_CAPABILITY_GRANT")
    op.drop_index(op.f("ix_PROJECT_protocol_version_id"), table_name="PROJECT")
    op.drop_constraint("fk_project_protocol_version", "PROJECT", type_="foreignkey")
    op.drop_column("PROJECT", "protocol_version_id")
    op.execute('DROP TRIGGER protocol_version_immutable ON "PROTOCOL_VERSION"')
    op.execute("DROP FUNCTION prevent_published_protocol_version_mutation()")
    op.drop_table("PROTOCOL_VERSION")
    op.drop_table("PROTOCOL")
