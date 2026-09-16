# ELANORA disaster recovery

ELANORA recovery bundles pair one PostgreSQL dump with the project repositories
and institution assets from the same maintenance window. Bundles are encrypted
with AES-256-GCM, authenticated before extraction, and contain a SHA-256 and byte
size for every archived file.

Run `make test-recovery` from the repository root to exercise the complete
procedure against disposable PostgreSQL and storage: seed data, dump, encrypt,
destroy the source database, restore into an empty database and storage root,
then verify the revision ledger, EAF projection, and institution asset.

The same-host `recovery-cache` is not a disaster backup: it is a working copy
the application refreshes as it writes. The backups described below are the
recoverable ones. ELANORA stores linked audiovisual media as references, not
managed objects; the institution must back up those source recordings
separately.

## Backups this installation takes for itself

An institution installs ELANORA; it does not staff a platform team. The
installation therefore runs its own maintenance in the `maintenance-worker`
service that ships with the composition. No cron entry is needed on the host.

It takes an encrypted backup of the database, project storage and institution
assets every 24 hours, verifies the newest backup weekly, applies each
project's retention policy daily, and checks hourly how full the disk holding
project storage is. What runs next is decided from the runs recorded in
PostgreSQL, so restarting never repeats a backup and a window missed while the
installation was switched off is caught up at the next wake-up. A failed job is
retried within the hour; one skipped because it is not configured waits, rather
than recording a row every few minutes.

**Administrators see the result** on the operations page: when the last backup
ran, when it was last verified, whether backups are healthy, failing or not
configured, and how full the disk is. An installation with no backup passphrase
is called out there, because otherwise nobody discovers there is nothing to
restore until the day they need it.

### What setup configures for you

`elanora-setup` generates every secret the installation needs, including the
passphrase that encrypts its backups, and keeps any value already present.
Running it again is safe: it never rotates an existing passphrase, which would
make every backup taken so far unreadable.

### Where backups are written

The composition mounts `./backups` into the maintenance worker as the default
destination, so a fresh installation is recoverable without any configuration.
That directory is on the same host as the installation, which protects against
losing the database or a bad upgrade, but **not** against losing the machine.
Point it at institution-controlled storage off this host, or use an
S3-compatible service:

| Setting | Meaning |
| --- | --- |
| `BACKUP_STORAGE_BACKEND` | `local` or `s3`. |
| `BACKUP_LOCAL_ROOT` | Directory for `local`; mount external storage there. |
| `BACKUP_S3_BUCKET`, `BACKUP_S3_PREFIX`, `BACKUP_S3_REGION`, `BACKUP_S3_ENDPOINT_URL` | Object store for `s3`; any S3-compatible service works. |
| `BACKUP_S3_ACCESS_KEY_ID`, `BACKUP_S3_SECRET_ACCESS_KEY` | Credentials, set together. |
| `BACKUP_RETAIN_COPIES` | How many copies to keep, 14 by default. |

### Running it by hand

The same work can be run on demand; it takes the same lock as the worker, so
the two never back up at once.

```sh
poetry run elanora-maintenance --once      # run whatever is due now
poetry run elanora-backup list             # what is stored, oldest first
poetry run elanora-backup verify           # check the newest against its manifest
```

Verification proves a copy is readable and matches its manifest. It does not
replace the restore drill below, which is what measures the recovery time.

## Create a consistent bundle

Choose an institutional RPO and schedule this procedure accordingly. The current
filesystem/Git architecture requires a brief write-maintenance window so the SQL
dump and repositories describe one state.

1. Prevent uploads, merges, restores, renames, project configuration changes, and
   asset replacement. Stop the backend and outbox worker if no external
   maintenance control exists.
2. Keep PostgreSQL running and create a plain SQL dump with `pg_dump`. Do not put
   a database password or backup passphrase in shell history.
3. Export a passphrase through the process environment or secret manager. It must
   contain at least 16 characters:

   ```sh
   export ELANORA_BACKUP_PASSPHRASE
   ```

4. From `website/backend`, create the bundle using the paths belonging to that
   deployment:

   ```sh
   poetry run elanora-disaster-recovery create \
     --database-dump /secure-staging/elanora.sql \
     --projects /var/lib/elanora/elanora_projects \
     --assets /var/lib/elanora/instance-assets \
     --output /secure-staging/elanora-2026-09-10.elanora
   ```

5. Verify the encrypted result before resuming writes or transferring it:

   ```sh
   poetry run elanora-disaster-recovery verify \
     /secure-staging/elanora-2026-09-10.elanora
   ```

6. Remove the unencrypted SQL staging file using the institution's secure-delete
   and retention procedure. Transfer the encrypted bundle off-host.

If files change between manifesting and archiving, bundle verification fails.
Never retain or distribute an unverified bundle.

## Restore drill

Always rehearse into an isolated, empty environment. Never extract over live
data.

1. Provision an empty PostgreSQL database and an empty storage location.
2. Extract to a path that does not yet exist:

   ```sh
   poetry run elanora-disaster-recovery extract \
     /off-host/elanora-2026-09-10.elanora \
     --destination /restore-drill/elanora
   ```

3. Import `/restore-drill/elanora/database.sql` with `psql`.
4. Configure `ELAN_PROJECTS_BASE_PATH` to
   `/restore-drill/elanora/projects` and `INSTANCE_ASSETS_BASE_PATH` to
   `/restore-drill/elanora/instance-assets`.
5. Run `alembic upgrade head`, start ELANORA, then run
   `elanora-check-integrity`. Every accepted project must report `healthy`.
6. Confirm administrator login, project permissions, contribution history,
   research topics, baseline tiers, logo delivery, EAF downloads, and a semantic
   contribution preview. Verify external media URLs separately.
7. Record elapsed restore time, snapshot age, bundle identifier, integrity
   result, and reviewer. Compare these with the institution's RTO and RPO.

Keep the drill isolated until review is complete, then destroy it under the
institution's data-handling policy.
