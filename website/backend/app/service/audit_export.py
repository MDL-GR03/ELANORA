"""Exporting the audit trail an institution has to be able to show.

Data classification and retention are recorded so the institution can answer an
ethics board or a data protection authority. That evidence has to be able to
leave the installation in a form a person can read and file, filtered to the
project and period actually being asked about.
"""

import csv
import json
from datetime import datetime
from typing import IO, Any, Literal, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.audit_event import AuditEvent

ExportFormat = Literal["json", "csv"]
COLUMNS = (
    "occurred_at",
    "action",
    "actor_user_id",
    "project_id",
    "resource_type",
    "resource_id",
    "details",
)


def _row(event: AuditEvent) -> dict[str, object]:
    return {
        "occurred_at": event.occurred_at.isoformat(),
        "action": event.action,
        "actor_user_id": event.actor_user_id,
        "project_id": event.project_id,
        "resource_type": event.resource_type,
        "resource_id": event.resource_id,
        "details": event.details,
    }


async def export_audit_events(
    db: AsyncSession,
    output: IO[str],
    *,
    project_id: int | None = None,
    since: datetime | None = None,
    until: datetime | None = None,
    output_format: ExportFormat = "json",
) -> int:
    """Write the matching audit trail, oldest first, and report how many."""
    statement = select(AuditEvent).order_by(AuditEvent.occurred_at)
    if project_id is not None:
        statement = statement.where(AuditEvent.project_id == project_id)
    if since is not None:
        statement = statement.where(AuditEvent.occurred_at >= since)
    if until is not None:
        statement = statement.where(AuditEvent.occurred_at <= until)
    rows = [_row(event) for event in (await db.scalars(statement)).all()]

    if output_format == "csv":
        writer = csv.DictWriter(output, fieldnames=list(COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow(cast(dict[str, Any], {**row, "details": json.dumps(row["details"])}))
    else:
        json.dump(rows, output, indent=2, sort_keys=True)
    return len(rows)
