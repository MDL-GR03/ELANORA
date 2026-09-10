"""Add an immutable ledger for accepted project revisions.

Revision ID: 0023
Revises: 0022
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "PROJECT_REVISION",
        sa.Column("revision_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("git_commit", sa.String(length=64), nullable=False),
        sa.Column("parent_git_commit", sa.String(length=64), nullable=True),
        sa.Column("source_type", sa.String(length=20), nullable=False),
        sa.Column("contribution_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.CheckConstraint("ordinal > 0", name="ck_project_revision_ordinal_positive"),
        sa.CheckConstraint(
            "source_type IN ('contribution', 'restoration', 'migration')",
            name="ck_project_revision_source_type",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["contribution_id"], ["PENDING_UPLOAD.upload_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("revision_id"),
        sa.UniqueConstraint(
            "project_id", "git_commit", name="uq_project_revision_commit"
        ),
        sa.UniqueConstraint(
            "project_id", "ordinal", name="uq_project_revision_ordinal"
        ),
    )
    op.create_index(
        op.f("ix_PROJECT_REVISION_project_id"),
        "PROJECT_REVISION",
        ["project_id"],
        unique=False,
    )

    # Preserve the provenance already recorded by earlier releases. Audit rows
    # without a usable commit remain in AUDIT_EVENT and are not invented here.
    op.execute(
        sa.text(
            """
            INSERT INTO "PROJECT_REVISION" (
                revision_id, project_id, ordinal, git_commit,
                parent_git_commit, source_type, contribution_id,
                actor_user_id, details, created_at
            )
            SELECT
                gen_random_uuid(), source.project_id,
                row_number() OVER (
                    PARTITION BY source.project_id
                    ORDER BY source.occurred_at, source.event_id
                ),
                source.git_commit, source.parent_git_commit, source.source_type,
                source.contribution_id, source.actor_user_id,
                source.details, source.occurred_at
            FROM (
                SELECT DISTINCT ON (
                    event.project_id,
                    COALESCE(
                        event.details ->> 'accepted_commit',
                        event.details ->> 'restored_commit'
                    )
                )
                    event.event_id,
                    event.project_id,
                    event.actor_user_id,
                    event.details,
                    event.occurred_at,
                    COALESCE(
                        event.details ->> 'accepted_commit',
                        event.details ->> 'restored_commit'
                    ) AS git_commit,
                    CASE
                        WHEN event.action = 'contribution.accepted'
                            THEN event.details ->> 'base_commit'
                        ELSE event.details ->> 'previous_commit'
                    END AS parent_git_commit,
                    CASE
                        WHEN event.action = 'contribution.accepted'
                            THEN 'contribution'
                        ELSE 'restoration'
                    END AS source_type,
                    pending.upload_id AS contribution_id
                FROM "AUDIT_EVENT" AS event
                LEFT JOIN "PENDING_UPLOAD" AS pending
                    ON event.action = 'contribution.accepted'
                   AND event.resource_id ~ '^[0-9]+$'
                   AND pending.upload_id = event.resource_id::integer
                WHERE event.project_id IS NOT NULL
                  AND event.action IN (
                      'contribution.accepted', 'project.version.restored'
                  )
                  AND COALESCE(
                      event.details ->> 'accepted_commit',
                      event.details ->> 'restored_commit'
                  ) ~ '^[0-9a-fA-F]{7,64}$'
                ORDER BY
                    event.project_id,
                    COALESCE(
                        event.details ->> 'accepted_commit',
                        event.details ->> 'restored_commit'
                    ),
                    event.occurred_at,
                    event.event_id
            ) AS source
            """
        )
    )
    op.execute(
        """
        CREATE FUNCTION prevent_project_revision_mutation()
        RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'PROJECT_REVISION is append-only';
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        CREATE TRIGGER project_revision_no_update_or_delete
        BEFORE UPDATE OR DELETE ON "PROJECT_REVISION"
        FOR EACH ROW EXECUTE FUNCTION prevent_project_revision_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        'DROP TRIGGER project_revision_no_update_or_delete ON "PROJECT_REVISION"'
    )
    op.execute("DROP FUNCTION prevent_project_revision_mutation()")
    op.drop_index(op.f("ix_PROJECT_REVISION_project_id"), table_name="PROJECT_REVISION")
    op.drop_table("PROJECT_REVISION")
