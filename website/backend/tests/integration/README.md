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
