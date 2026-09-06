# Database migrations

Alembic is the only supported way to create or update an ELANORA database.

```bash
poetry run alembic upgrade head
poetry run alembic check
```

Set `DATABASE_URL` to an async SQLAlchemy URL, normally
`postgresql+asyncpg://user:password@host:5432/database`. New revisions must be
reviewed and must include both upgrade and downgrade behavior.
