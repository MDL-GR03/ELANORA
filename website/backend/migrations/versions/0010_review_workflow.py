"""Add revision-oriented contribution review cases.

Revision ID: 0010
Revises: 0009
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "REVIEW_CASE",
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("upload_id", sa.Integer(), nullable=False),
        sa.Column("resubmitted_upload_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("filename", sa.String(length=512), nullable=True),
        sa.Column("tier_id", sa.String(length=255), nullable=True),
        sa.Column("annotation_id", sa.String(length=255), nullable=True),
        sa.Column("validation_issue_id", sa.Uuid(), nullable=True),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "state IN ('open','changes_requested','resubmitted','resolved','closed')",
            name="ck_review_case_state",
        ),
        sa.CheckConstraint(
            "start_ms IS NULL OR start_ms >= 0", name="ck_review_case_start_ms"
        ),
        sa.CheckConstraint(
            "end_ms IS NULL OR end_ms >= start_ms", name="ck_review_case_interval"
        ),
        sa.ForeignKeyConstraint(
            ["project_id"], ["PROJECT.project_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["upload_id"], ["PENDING_UPLOAD.upload_id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["resubmitted_upload_id"],
            ["PENDING_UPLOAD.upload_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["validation_issue_id"],
            ["VALIDATION_ISSUE.validation_issue_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["created_by"], ["USER.user_id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["assigned_to"], ["USER.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("case_id"),
    )
    op.create_index("ix_REVIEW_CASE_upload_id", "REVIEW_CASE", ["upload_id"])
    op.create_index(
        "ix_review_case_project_state", "REVIEW_CASE", ["project_id", "state"]
    )
    op.create_table(
        "REVIEW_COMMENT",
        sa.Column("comment_id", sa.Uuid(), nullable=False),
        sa.Column("case_id", sa.Uuid(), nullable=False),
        sa.Column("author_user_id", sa.Integer(), nullable=True),
        sa.Column("parent_comment_id", sa.Uuid(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["case_id"], ["REVIEW_CASE.case_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["author_user_id"], ["USER.user_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"],
            ["REVIEW_COMMENT.comment_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_index("ix_REVIEW_COMMENT_case_id", "REVIEW_COMMENT", ["case_id"])
    op.drop_table("COMMENT_CONFLICT")
    op.drop_table("COMMENT_ELAN_FILE")
    op.drop_table("COMMENT_PROJECT")
    op.drop_table("USER_WORK_ON_CONFLICT")
    op.drop_table("CONFLICT_OF_ELAN_FILE")
    op.drop_table("COMMENT")
    op.drop_table("CONFLICT")
    op.execute("DROP TYPE IF EXISTS commenttargettype")


def downgrade() -> None:
    op.create_table(
        "CONFLICT",
        sa.Column("conflict_id", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("conflict_id"),
    )
    op.create_table(
        "COMMENT",
        sa.Column("comment_id", sa.String(length=50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "target_type",
            sa.Enum(
                "PROJECT",
                "ELAN_FILE",
                "CONFLICT",
                "TIER",
                "ANNOTATION",
                name="commenttargettype",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("parent_comment_id", sa.String(length=50), nullable=True),
        sa.ForeignKeyConstraint(
            ["parent_comment_id"], ["COMMENT.comment_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["USER.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_table(
        "CONFLICT_OF_ELAN_FILE",
        sa.Column("conflict_id", sa.String(length=50), nullable=False),
        sa.Column("elan_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["conflict_id"], ["CONFLICT.conflict_id"]),
        sa.ForeignKeyConstraint(["elan_id"], ["ELAN_FILE.elan_id"]),
        sa.PrimaryKeyConstraint("conflict_id", "elan_id"),
    )
    op.create_table(
        "USER_WORK_ON_CONFLICT",
        sa.Column("conflict_id", sa.String(length=50), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["conflict_id"], ["CONFLICT.conflict_id"]),
        sa.ForeignKeyConstraint(["user_id"], ["USER.user_id"]),
        sa.PrimaryKeyConstraint("conflict_id", "user_id"),
    )
    op.create_table(
        "COMMENT_PROJECT",
        sa.Column("comment_id", sa.String(length=50), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["COMMENT.comment_id"]),
        sa.ForeignKeyConstraint(["project_id"], ["PROJECT.project_id"]),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_table(
        "COMMENT_ELAN_FILE",
        sa.Column("comment_id", sa.String(length=50), nullable=False),
        sa.Column("elan_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["COMMENT.comment_id"]),
        sa.ForeignKeyConstraint(["elan_id"], ["ELAN_FILE.elan_id"]),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.create_table(
        "COMMENT_CONFLICT",
        sa.Column("comment_id", sa.String(length=50), nullable=False),
        sa.Column("conflict_id", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["COMMENT.comment_id"]),
        sa.ForeignKeyConstraint(["conflict_id"], ["CONFLICT.conflict_id"]),
        sa.PrimaryKeyConstraint("comment_id"),
    )
    op.drop_index("ix_REVIEW_COMMENT_case_id", table_name="REVIEW_COMMENT")
    op.drop_table("REVIEW_COMMENT")
    op.drop_index("ix_review_case_project_state", table_name="REVIEW_CASE")
    op.drop_index("ix_REVIEW_CASE_upload_id", table_name="REVIEW_CASE")
    op.drop_table("REVIEW_CASE")
