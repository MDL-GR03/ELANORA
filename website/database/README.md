# Legacy database artifacts

## PostgreSQL schema source of truth

ELANORA does not keep a hand-edited `schema.sql`. The schema is reproducible
from two version-controlled layers:

1. SQLAlchemy models under `website/backend/app/model` describe the schema the
   current application expects.
2. Alembic revisions under `website/backend/migrations/versions` describe every
   ordered change required to reach it from an empty or older installation.

The database records its applied revision in the `alembic_version` table. On
startup, the backend runs `alembic upgrade head`, applying only revisions newer
than that recorded value. Existing rows and the Docker volume are retained.

Useful development commands are:

```bash
make dev-db-current  # revision currently applied to the running database
make dev-db-history  # ordered, version-controlled migration history
make dev-db-schema   # inspect PostgreSQL DDL without dumping research data
```

To change the schema, edit the SQLAlchemy model, generate a candidate revision,
review the generated operations, and test both directions:

```bash
cd website/backend
poetry run alembic revision --autogenerate -m "add review assignment index"
poetry run alembic upgrade head
poetry run alembic downgrade -1
poetry run alembic upgrade head
```

Only run downgrade against a disposable development/test database. Production
rollbacks should normally deploy a forward corrective migration, especially
after a revision has transformed or removed data. Commit the model and its
reviewed migration together. A schema-only `pg_dump` is useful for inspection
or external audit, but it is generated output—not the source of truth.

## Relation to MySQL

PostgreSQL still uses databases, tables, rows, primary keys, foreign keys,
indexes, transactions, and SQL. The main operational difference here is that
ELANORA uses PostgreSQL-specific drivers and Alembic rather than importing a
MySQL dump. PostgreSQL's `public` schema is a namespace inside the `elanora`
database; it is not a replacement for the database itself. In this project,
"schema migration" means a versioned structural change, while "schema" may
also mean that PostgreSQL namespace.

The Docker named volume `elanora_db_dev` stores the actual development database
files. `make dev-down` stops containers and preserves that volume. Removing the
volume erases the development database, after which Alembic recreates the
structure and the browser bootstrap creates initial institutional data. For
portable backups use PostgreSQL's `pg_dump`/`pg_restore`, not a copy of the
volume and not the historical MySQL dump.

## MySQL-era import

SQL dumps are no longer an installation mechanism. ELANORA uses PostgreSQL and
versioned Alembic migrations from `website/backend/migrations`.

The untracked `dump.sql` found in some development checkouts is a legacy MySQL
server dump. It includes server-system tables, must not be committed, and must
never be executed against PostgreSQL or edited in place.

The guarded one-way importer verifies this repository's reviewed dump checksum,
refuses a non-empty target, copies compatible institutional and configuration
records, and reconstructs EAF, tier, annotation, and immutable-revision records
from validated source EAF bytes. Reconstruction matters because legacy tiers
were shared across files while the corrected PostgreSQL model scopes every tier
to one EAF.

Validate the conversion in a separate PostgreSQL 18 database and project-data
volume:

```bash
make legacy-validate
make legacy-status
make legacy-down
```

The isolated database listens on local port `5417`; normal development remains
on `5416`. `legacy-down` retains validation data. Removing it requires the
explicit destructive command below:

```bash
docker compose -f website/docker/legacy-migration/docker-compose.yml down -v
```
