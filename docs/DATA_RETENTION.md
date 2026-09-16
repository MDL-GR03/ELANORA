# Data governance and retention

Each project records how sensitive its research data is and how long that data
is kept. Project administrators set this in **Project settings → Data
Governance**; members can read it. Every change is audited with the values
before and after.

## What a project records

| Field | Meaning |
| --- | --- |
| Data classification | `public`, `internal`, `confidential` or `sensitive_personal`. A project starts unclassified. |
| Legal basis | The lawful basis or consent reference behind the data. Required for sensitive personal data. |
| Retention period | Days a deleted project's content is kept before it may be purged. At least 30. Empty means kept until someone decides. |
| Legal hold | While set, nothing is purged, whatever the retention period. A hold requires a reason. |

The API refuses personal data without a legal basis, a hold without a reason,
and a retention period under 30 days. PostgreSQL check constraints refuse the
same, so a worker, script or migration cannot skip them.

## Purging content after retention

Deleting a project leaves a tombstone: the row remains, so its name stays
reserved and its audit history keeps meaning. The content is destroyed later,
by an explicit command:

```bash
poetry run elanora-purge-expired-projects --dry-run   # report what is due
poetry run elanora-purge-expired-projects             # destroy it
```

A project is purged only when all of these hold: it is deleted, it has a
retention period, that period has passed, and no legal hold is in place. Run it
from a scheduled job (for example a nightly systemd timer or cron entry); each
run reports what it purged as JSON.

A purge destroys the project's ELAN files with their annotations and revisions,
its revision manifests, its contributions and reviews, its rejected upload
attempts, its compliance scans, the validation evidence for the destroyed
revisions, and its Git export and same-host recovery copy. File content shared
with another project through identical bytes is kept. What remains is the
project row with its governance, its members, and the audit events, including
one recording what the purge destroyed.

## Answering a compliance request

An ethics board or data protection authority asks what was held, why, and when
it was destroyed. The audit trail answers that, and can be exported:

```bash
poetry run elanora-export-audit --project-id 12 --format csv --output audit.csv
poetry run elanora-export-audit --since 2026-01-01 --until 2026-06-30
```

Events come out oldest first, and carry the moment, the action, who acted, the
project and resource, and the recorded detail. Purges appear as
`project.content.purged` with what was destroyed; classification changes appear
as `project.data_governance.updated` with the values before and after.

## Participant withdrawal

This is deliberately not automated. ELANORA has no reliable participant
identity: the EAF `PARTICIPANT` tier attribute is free text an annotator types,
inconsistent between files, and good practice is a pseudonymous code whose
mapping to a real person is kept outside these files entirely. Software cannot
safely decide which annotations belong to a person who has withdrawn.

An administrator handles a withdrawal: locate the affected file or files, edit
or remove the content, and the action is recorded in the audit trail like any
other. Deletion-adjacent actions require project-admin permission; a
contributor has no path to delete accepted content.

## Why a purge can delete immutable rows

Revision manifests and validation evidence are append-only: PostgreSQL triggers
refuse updates and deletes. A purge runs in a transaction that sets
`elanora.allow_retention_purge`, which those triggers accept, so destroying
research data is always deliberate and never a side effect of an application
bug.

Until migration 0036 the guards compared `current_setting(..., true)` with
`'on'` directly. With the setting absent, which is every ordinary transaction,
the comparison is NULL rather than false, so the guard never raised and those
rows could be deleted by anything holding a database session. Each guard now
reads the setting through `coalesce`, and integration tests delete from every
protected table to prove the refusal.
