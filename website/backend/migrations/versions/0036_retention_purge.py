"""Allow a retention purge to remove a deleted project's immutable content.

Revision history and validation evidence stay append-only for every ordinary
writer. A purge runs in a transaction that sets elanora.allow_retention_purge,
so destroying research data is always a deliberate act, recorded in the audit
trail, and never a side effect of an application bug.

This also repairs the existing guards. They read
``NOT (TG_OP = 'DELETE' AND current_setting(..., true) = 'on')``: with the
setting absent, which is every ordinary transaction, current_setting returns
NULL, the comparison is NULL, and the guard never fired. Published protocol
versions and validation evidence could therefore be deleted by anything holding
a database session. Every guard now reads the setting through coalesce, so an
absent setting means "not purging".

Revision ID: 0036
Revises: 0035
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0036"
down_revision: str | None = "0035"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PURGING = (
    "coalesce(current_setting('elanora.allow_retention_purge', true), 'off') = 'on'"
)
PROTOCOL_PURGING = (
    "coalesce(current_setting('elanora.allow_protocol_purge', true), 'off') = 'on'"
)


def upgrade() -> None:
    op.add_column(
        "PROJECT",
        sa.Column("content_purged_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION prevent_project_revision_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF NOT (TG_OP = 'DELETE' AND {PURGING}) THEN
                RAISE EXCEPTION 'PROJECT_REVISION is append-only';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION prevent_project_revision_eaf_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF NOT (TG_OP = 'DELETE' AND {PURGING}) THEN
                RAISE EXCEPTION 'PROJECT_REVISION_EAF is append-only';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION prevent_immutable_validation_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF NOT (
                TG_OP = 'DELETE' AND ({PROTOCOL_PURGING} OR {PURGING})
            ) THEN
                RAISE EXCEPTION 'validation evidence is immutable';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION prevent_published_protocol_version_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'published'
                AND NOT (TG_OP = 'DELETE' AND {PROTOCOL_PURGING}) THEN
                RAISE EXCEPTION 'published protocol versions are immutable';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql
        """
    )


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_project_revision_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'PROJECT_REVISION is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_project_revision_eaf_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'PROJECT_REVISION_EAF is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_immutable_validation_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF NOT (
                TG_OP = 'DELETE' AND
                current_setting('elanora.allow_protocol_purge', true) = 'on'
            ) THEN
                RAISE EXCEPTION 'validation evidence is immutable';
            END IF;
            RETURN OLD;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_published_protocol_version_mutation()
        RETURNS trigger AS $$
        BEGIN
            IF OLD.status = 'published' AND NOT (
                TG_OP = 'DELETE' AND
                current_setting('elanora.allow_protocol_purge', true) = 'on'
            ) THEN
                RAISE EXCEPTION 'published protocol versions are immutable';
            END IF;
            RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.drop_column("PROJECT", "content_purged_at")
