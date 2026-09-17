# Contributing to ELANORA

ELANORA protects research annotations, so correctness and reproducibility take
priority over delivery speed. Changes should preserve the original `.eaf`
bytes, keep database migrations reversible, and include a test for every fixed
defect or new rule.

## Development workflow

Create `feature/<name>`, `fix/<name>`, `test/<name>`, or `docs/<name>` branches
from `dev`. Open a pull request back to `dev`; releases merge through `main`.
Use [Conventional Commits](https://www.conventionalcommits.org/), for example
`fix(eaf): reject dangling annotation references`.

Do not commit secrets, real participant data, generated coverage output,
database files, or local environment files. The files under `website/static`
and `website/backend/tests/fixtures` must remain public-safe test data.

## Backend

The backend requires Python 3.13 and Poetry 2. Run commands from
`website/backend`:

```bash
poetry install
poetry run ruff format --check .
poetry run ruff check .
poetry run mypy --config-file mypy.ini
poetry run pytest tests/unit --cov=app --cov-report=term-missing
poetry run pip-audit
```

Database integration tests require PostgreSQL rather than SQLite. From the
repository root, run `make test-integration`, or run `make backend-check` for
the complete backend gate. The test stack is isolated from development and is
destroyed after a successful run.

`mypy.ini` checks the whole `app` package in strict mode, so every new module
must be fully typed from its first commit. Do not add anonymous `dict`
structures where a dataclass, Pydantic request/response model, or typed record
describes a stable contract. A pull request must not weaken strictness, add
`type: ignore` comments to silence real findings, or exclude a module from the
check.

### EAF changes

EAF ingestion has two required validation layers: the vendored official ELAN
3.0 XSD and ELANORA's cross-reference and semantic checks. Parsing must use the
typed models in `app/elan`, retain the exact original bytes and SHA-256 digest,
and preserve unknown XML attributes and elements for forward compatibility.

Add focused malformed-document tests and at least one realistic end-to-end
fixture assertion. Run the EAF suite directly with:

```bash
poetry run pytest tests/unit/test_eaf_parser.py tests/unit/test_elan_validation.py
```

Never silently repair a source document during ingestion. Report validation
issues to the researcher and store a new immutable revision only after the
document passes.

### Database changes

SQLAlchemy models are the application model; Alembic migrations are the
deployment history. After changing a model:

```bash
poetry run alembic revision --autogenerate -m "describe the change"
```

Review generated migrations by hand. Test both upgrade and downgrade, avoid
data-destructive transformations, and use expand, migrate, and contract steps
for deployed databases. The SQL dump under `website/database` is historical
reference only. `make test-integration` exercises the latest downgrade and
upgrade and runs `alembic check`, which fails when SQLAlchemy models and the
migration head have drifted apart. Run migration verification against disposable PostgreSQL with
`make test-db-reset`, use its `TEST_DATABASE_URL` documented in the integration
test guide, and finish with `make test-db-down`.

## Frontend

The frontend requires Node.js 24. Run commands from `website/frontend`:

```bash
npm ci
npm run lint
npm run stylelint
npm run format
npm run test
npm run build
npm audit --audit-level=high
```

Use `npm run lint:fix`, `npm run stylelint:fix`, and `npm run format:fix` for
local repairs. `npm run test:watch` provides the interactive Vitest workflow;
`npm run test` is deterministic and exits for CI.

## Pull-request checklist

- The backend and frontend commands above pass for the changed areas.
- Behavior changes have realistic tests and failure-path coverage.
- EAF source fidelity and validation rules remain intact.
- Schema changes include reviewed reversible migrations.
- Authorization is checked at the project boundary, not only in the UI.
- Logs and API errors contain no tokens, passwords, participant data, or
  internal exception details.
- Documentation and example environment variables reflect the change.

Questions and design proposals belong in this repository's issue tracker or
discussion board.
