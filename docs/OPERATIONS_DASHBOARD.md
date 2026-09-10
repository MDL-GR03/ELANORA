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
