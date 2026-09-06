# Server-change recovery workflow

The **Review server changes** action is an administrator recovery boundary. It
is not a second upload mechanism and should not be part of normal researcher
work. It exists for exceptional edits made directly below a project's
`elan_files` directory.

Each accepted attempt is coordinated as a durable saga because PostgreSQL,
Git, and filesystem storage cannot share one atomic transaction:

1. A `PROJECT_SYNC_OPERATION` row records the project, administrator, starting
   Git commit, detected changes, and state `preparing`.
2. Current source bytes and a SHA-256 manifest are copied to protected staging
   storage.
3. The entire EAF batch is validated before Git staging or database processing.
4. The operation advances through `prepared` and `committing`.
5. The accepted Git commit contains an `ELANORA-Sync-Operation` trailer.
6. PostgreSQL records the result commit and state `completed`.

An interrupted operation is `failed` when canonical Git history did not change.
It becomes `recovery_required` only when a new Git commit exists but completion
was not recorded. Recovery is permitted only when that commit matches the
recorded operation. ELANORA then rebuilds the database projection from all
validated canonical EAF files and completes that same operation.

Discarding server changes is also durable: ELANORA preserves the changed bytes
and hashes before resetting the worktree, records a `discarded` operation, and
emits an append-only audit event. Completion, failure, and recovery outcomes
also emit audit events linked to the operation UUID.

Successful evidence expires after 30 days and is removed when operation
history is maintained. Failed and recovery-required evidence has no automatic
expiry. Operation metadata and content hashes remain in PostgreSQL.

The staging root is configured with `SYNC_STAGING_BASE_PATH`. It must reside on
the persistent protected ELANORA data volume and must not be served by the web
server.
