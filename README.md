# ELANORA

ELANORA is a prototype collaboration and quality-governance platform for ELAN
Annotation Format (`.eaf`) research projects. It combines institutional project
management, membership and invitations, configurable naming standards, upload
review, and revision history for sign-language research teams.

> **Current status:** hardened pre-production prototype. Core EAF validation,
> immutable source revisions, project authorization, PostgreSQL migrations,
> concurrency locks, tests, and CI are implemented. A production deployment
> still needs institution-specific privacy review, external object storage,
> off-host backups, restore drills, and operational monitoring.

Start with the [repository and architecture audit](docs/AUDIT_2026-08.md). It
describes the implemented system, verified findings, target architecture,
database recommendation, and phased recovery plan.

## Repository layout

- `website/backend`: FastAPI, SQLAlchemy, EAF parsing, and Git workflows
- `website/frontend`: Vue 3 and Vite client
- `website/docker`: development, production, and server Compose prototypes
- `website/static`: sanitized/sample EAF corpora used during development
- `installer`: institutional instance setup prototype
- `docs`: design artifacts, database drafts, prototype screens, and audit

See [CONTRIBUTING.md](CONTRIBUTING.md) for the enforced development commands and
[`website/docker/README.md`](website/docker/README.md) for deployment setup.

## Local development

With Docker and Docker Compose installed:

```bash
make dev-up
make dev-bootstrap
```

Then open <http://localhost:8777>. Migrations run automatically during backend
startup. `make dev-bootstrap` is needed only for a new database volume; it
prompts for the initial administrator password. Run `make help` to see the
remaining development and verification commands.

Run the complete quality gate with `make check`. Database integration tests use
a disposable PostgreSQL 18 instance rather than SQLite or a mutable baseline
dump. See the [integration-test guide](website/backend/tests/integration/README.md)
and the [current architecture roadmap](docs/ARCHITECTURE_ROADMAP_2026-09.md).
