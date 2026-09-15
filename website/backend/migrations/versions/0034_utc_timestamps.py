"""Store every remaining naive timestamp as an explicit UTC instant.

These columns were TIMESTAMP WITHOUT TIME ZONE. Their values came from
PostgreSQL's clock or the application server's local clock; ELANORA's
containers run in UTC, so existing values are interpreted as UTC.

Revision ID: 0034
Revises: 0033
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0034"
down_revision: str | None = "0033"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

COLUMNS: tuple[tuple[str, str], ...] = (
    ("ADDRESS", "created_at"),
    ("ADDRESS", "updated_at"),
    ("CITY", "created_at"),
    ("CITY", "updated_at"),
    ("COUNTRY", "created_at"),
    ("COUNTRY", "updated_at"),
    ("ELAN_FILE", "last_modified"),
    ("FILE_CONTENT", "created_at"),
    ("INVITATION", "created_at"),
    ("INVITATION", "expires_at"),
    ("INVITATION", "responded_at"),
    ("NOTIFICATION", "created_at"),
    ("NOTIFICATION_PREFERENCE", "created_at"),
    ("NOTIFICATION_PREFERENCE", "updated_at"),
    ("PENDING_UPLOAD", "detected_at"),
    ("PENDING_UPLOAD", "resolved_at"),
)


def upgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITH TIME ZONE USING \"{column}\" AT TIME ZONE 'UTC'"
        )


def downgrade() -> None:
    for table, column in COLUMNS:
        op.execute(
            f'ALTER TABLE "{table}" ALTER COLUMN "{column}" '
            f"TYPE TIMESTAMP WITHOUT TIME ZONE USING \"{column}\" AT TIME ZONE 'UTC'"
        )
