"""Permit a transaction-scoped purge of unused protocol evidence.

Revision ID: 0015
Revises: 0014
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0015"
down_revision: str | None = "0014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
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


def downgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION prevent_published_protocol_version_mutation()
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
        CREATE OR REPLACE FUNCTION prevent_immutable_validation_evidence_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'validation evidence is immutable';
        END;
        $$ LANGUAGE plpgsql
        """
    )
