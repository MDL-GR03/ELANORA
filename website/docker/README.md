# Container deployment

ELANORA uses PostgreSQL 18 and applies Alembic migrations before the backend
starts. The Compose files are environment-specific examples, not a substitute
for an institution's backup, TLS, monitoring, and secret-management platform.

Copy `../.env.example` beside the selected Compose file and replace every
placeholder. Application variables may also be supplied through the existing
environment-file mechanism. Internet-facing `prod` and `server` deployments
must provide `ENVIRONMENT`, a random `JWT_SECRET_KEY` of at least 32 characters,
HTTPS `FRONTEND_HOST` and `BACKEND_HOST` origins, mail configuration, and
database credentials. Do not commit the resulting `.env` files.

The development stack reads its configuration from `website/env/.env.dev.docker`.
`make dev-up` creates this file from the committed example on first run:

```bash
make dev-up
make dev-bootstrap
make dev-email-smoke
```

Open `http://localhost:8025` to inspect the captured recipient, headers, text,
HTML, links, and rendering. Production and server stacks do not include Mailpit
and continue to require institution-managed SMTP settings.

`make dev-email-smoke` queues encrypted account-verification and password-reset
events, lets the normal outbox worker decrypt and deliver them, and asserts both
captured message bodies through Mailpit. It therefore checks the same durable
path used by the authentication API rather than bypassing the worker.

`make dev-up` builds the containers, waits for PostgreSQL, applies all Alembic
migrations, starts the API and frontend, and waits for their health checks.
Bootstrap is interactive and requests the administrator password without echo.
Later runs only need `make dev-up`. Use `make help` for logs, status, health,
shutdown, and test commands. Backend Python changes reload Uvicorn and frontend
Vue, JavaScript, and CSS changes are delivered through Vite hot-module
replacement; neither workflow requires rebuilding an image.

The stack also runs a dedicated outbox worker. Existing-user invitation emails
are recorded in PostgreSQL in the same transaction as their invitation and are
then delivered asynchronously. Normal retries require no manual action; use
`make dev-dispatch-outbox` to request an immediate one-off drain while debugging.

When a legacy database has already been migrated, sign in with its existing
username. If the original password is unavailable, reset it interactively:

```bash
make dev-reset-password
# Or select another account:
make dev-reset-password ELANORA_USER=another_username
```

The guarded legacy import is documented in `website/database/README.md` and can
be rehearsed against an isolated PostgreSQL database with
`make legacy-validate`. It never modifies the historical MySQL dump.

## Disposable database tests

Run database integration tests against an isolated PostgreSQL 18 container:

```bash
make test-integration
```

The test database listens only on `127.0.0.1:5418`; development remains on
`5416`. A successful run removes the test container and its data. Use
`make test-db-reset`, `make test-db-up`, and `make test-db-down` when debugging
the database manually. Test schema creation always uses Alembic, never an SQL
dump or SQLAlchemy `create_all()`.

To override the local-only database password, set `ELANORA_DEV_DB_PASSWORD`
in the invoking shell and edit `DB_PASSWORD` in `website/env/.env.dev.docker`
to match — the `db` service reads the shell variable, the backend reads the
env file. Production and server Compose configurations still require externally
managed secrets.

Before upgrading a deployed instance, take and verify an off-host PostgreSQL
backup and a versioned copy of the immutable EAF/media objects. Review the new
Alembic migration, test it on a restored copy, then deploy. A healthy container
is not proof of recoverability; schedule full restore drills and record RPO/RTO
results.

The local `.elanora_projects_backups` directory is a same-host recovery cache.
It survives ordinary project deletion, but it does not protect against disk
loss, ransomware, or host compromise and must not be described as a disaster
recovery backup.
