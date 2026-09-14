# System health and recovery dashboard

Institution administrators can open `/admin/operations` to inspect the active
asset-storage backend, corpus-integrity scan results, and the boundary between
ELANORA and deployment-managed disaster recovery.

The page never returns storage credentials, filesystem paths, encryption keys,
database connection details, or backup passphrases. S3 bucket names are masked
and only the endpoint hostname is shown. `POST /api/v1/operations/storage-check`
performs an explicit write, read, byte comparison, and cleanup using a unique
probe key. It does not touch an existing asset.

Backup scheduling and restoration remain deployment operations. This is
intentional: recovery credentials and backups must remain available when the
application database or server is unavailable. The dashboard therefore reports
recovery evidence as unavailable until an external scheduler can submit signed
job evidence through a future integration. Operators should run
`make test-recovery` regularly and retain its reports with their infrastructure
monitoring records.

For S3-compatible storage, infrastructure must separately enforce and monitor
bucket versioning, server-side encryption, retention, access logging, capacity,
and off-site replication. A successful application-level storage probe proves
only that ELANORA can currently write, read, and remove a test object.

## Email delivery and its retention policy

Invitation, account-verification and password-reset messages are recorded in
the PostgreSQL outbox before any mail is sent, so a mail-provider outage delays
delivery instead of losing it. The dispatcher retries an event up to
`MAX_DELIVERY_ATTEMPTS` times.

Two states are reported on the dashboard. *Awaiting delivery* counts events that
are still eligible for retry, alongside the age of the oldest one, so a stalled
dispatcher or a long provider outage becomes visible. *Given up on* counts
events that exhausted every attempt. That number matters operationally: those
messages never reached the person they were addressed to, and no automatic
process will try again, so an administrator must reissue the invitation or ask
the researcher to request a new code.

Retention follows the same principle as the rest of the outbox. A published
event has its payload discarded immediately, because the recipient address and
any personal message are no longer needed once delivery succeeded. An event that
is given up on is treated identically at the moment the final attempt fails: the
payload is cleared, leaving only the event type, subject identifier, attempt
count and timestamps. What survives is enough to tell an administrator that a
message of that kind never arrived, and not enough to say whose address it was.

The remaining metadata is deleted after `FAILED_EVENT_RETENTION_DAYS`. The
dispatcher applies this on each pass, so a deployment that runs
`elanora-dispatch-outbox` needs no separate cleanup job. The window can be
overridden per deployment with `--retention-days`.
