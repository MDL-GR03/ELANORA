# PostgreSQL integration tests

These tests run against PostgreSQL 18 after the complete Alembic migration
chain. They must not create tables with `Base.metadata.create_all()` or fall
back to SQLite: migration and PostgreSQL-specific behavior are part of what the
suite verifies.

From the repository root, run:

```bash
make test-integration
```

This command destroys only the dedicated `elanora-test` Compose project,
starts a clean database on `127.0.0.1:5418`, migrates it to `head`, executes the
integration suite, and removes the test container after success. It cannot
access or delete the development database on port `5416`.

For interactive debugging:

```bash
make test-db-reset
cd website/backend
ENVIRONMENT=test \
TEST_DATABASE_URL=postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test \
poetry run pytest tests/integration -vv
cd ../..
make test-db-down
```

The shared fixture truncates all application tables and resets sequences before
each test. Tests should construct only the domain state they require and use
public services or repositories rather than loading an opaque database dump.

## HTTP tests

`api_client` drives the real application from `app.main`, middleware included,
through httpx. Each request opens its own database session, as in production,
project storage and recovery copies live in a temporary directory, and cookies
follow their paths like a browser's. `institution_accounts` provides a verified
administrator, researcher and outsider sharing `ACCOUNT_PASSWORD`, and
`Browser` signs in and echoes the CSRF token on state-changing requests.

Prefer these for behaviour a person meets through the interface: sign-in,
permissions, uploads, reviews and protocol administration. Serialization,
cookie and transaction mistakes only show up at this level.
