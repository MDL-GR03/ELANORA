# ELANORA engineering state recap

**Assessment date:** 5 September 2026  
**Current stage:** hardened pre-production prototype  
**Deployment boundary:** one installation for one institution

For the current repository-wide cleanup inventory, removal candidates, and
four pending product decisions, see
[`REPOSITORY_CLEANUP_AUDIT_2026-09-05.md`](REPOSITORY_CLEANUP_AUDIT_2026-09-05.md).

## Executive state

ELANORA now has a reproducible PostgreSQL development and test baseline, a
lossless first-stage EAF ingestion path, centralized project authorization,
immutable revision and rejected-ingestion evidence, database migrations, CI,
and durable account-email delivery. The development stack starts with one
command, retains its database volume across normal restarts, supports frontend
and backend hot reload, and catches outbound mail in Mailpit.

This is a strong engineering base, but it is not yet appropriate for
identifiable research corpora. The remaining gaps are primarily product-domain
architecture and institutional operations rather than broken development
tooling: immutable protocol versions, a complete revision-scoped EAF
projection, object storage and verified backups, replacement of Git as the
transaction coordinator, privacy governance, and decomposition of oversized
feature modules.

## Objective comparison

| Product objective | Current evidence | Status |
| --- | --- | --- |
| One institution operates one isolated installation | The database enforces one institution profile; bootstrap is guarded; projects and users carry institution scope | Implemented baseline |
| Researchers collaborate around projects | Membership, invitations, permission checks, pending uploads, review and Git-backed history exist | Working prototype |
| Do not lose submitted research information | Exact EAF bytes, SHA-256 checksums, immutable revisions, and rejected ingestion attempts are retained | Implemented for EAF; media and off-host recovery pending |
| Ensure files remain valid ELAN documents | Hardened XML parsing, bundled EAF 3.0 XSD validation, semantic reference checks, real valid and malformed fixtures | Implemented baseline; golden corpus must grow |
| Enforce institutional annotation conventions | Immutable versions now govern required tiers, hierarchy, linguistic types, controlled vocabularies and media policy; legacy naming configuration remains | Partial; migrate filename and accepted-value rules |
| Provide Git-like traceability without Git-like complexity for researchers | Revision evidence and existing review screens exist, but mutable shared Git workflows still coordinate publication | Partial; revision-native change sets remain P0/P1 |
| Use a solid, maintainable database | PostgreSQL 18.6, async SQLAlchemy, Alembic, disposable integration database, constraints and UTC migration work | Strong baseline; more domain constraints and projection tables needed |
| Secure account and invitation workflows | Cookie/CSRF protections, project guards, atomic invitation membership, encrypted transactional email outbox and retry worker | Strong baseline; broader API-negative and idempotency tests remain |
| Easy local development | `make dev-up`, hot reload, persistent PostgreSQL volume, Mailpit, bootstrap/reset/smoke commands | Implemented |
| Production operability | Non-root production image, validated secrets, health checks and CI exist | Not ready: restore drills, monitoring, secret service and privacy review pending |
| Cross-institution collaboration | Stable installation identity provides a future anchor | Deliberately deferred; no federation is claimed |

## Closed in the latest slice

- Added institution-owned protocols with editable drafts and database-enforced
  immutable published versions.
- Added explicit project pinning, immutable validator releases, idempotent
  validation runs, ordered structured issues and audit events.
- Added the independent `manage_protocols` project capability. Administrators
  can delegate it in the members screen without granting unrelated project
  administration; PostgreSQL requires the recipient to be a project member.
- Added a complete real-EAF scenario covering publish, pin, successful
  validation, failed required-tier validation and immutable evidence.
- Added a project protocol editor for creating drafts, publishing immutable
  snapshots and assigning them to the project.
- Account verification and password-reset messages now commit atomically with
  encrypted PostgreSQL outbox records and are delivered by a retrying worker.
- Mailpit provides a local SMTP catcher and API-verifiable development test.
- Outbox keys are validated and rotatable; production rejects the development
  key; successful secret-bearing payloads are scrubbed.
- Backend and outbox containers run with the host UID/GID in development.
  Bind-mounted source, project and recovery paths are no longer written as
  root-owned files.
- Python logging writes only to standard error. Docker or the production
  service manager owns collection and rotation; obsolete source-tree log files
  and the unused logging example were removed.
- Development health and encrypted-email smoke tests pass against the live
  Compose stack without replacing the persistent development database.

## Verification evidence

The complete `make check` gate passed on 5 September 2026:

- Ruff format and lint: passed for 239 backend files;
- mypy: passed for the 27-file strict architectural boundary;
- backend unit tests: 60 passed;
- PostgreSQL integration tests: 30 passed after a clean nine-migration Alembic
  upgrade;
- frontend ESLint, Stylelint and Prettier: passed;
- frontend tests: 28 passed across 10 test files;
- production frontend build: passed;
- `pip-audit`: no known third-party vulnerabilities;
- `npm audit --audit-level=high`: zero vulnerabilities;
- development, production and server Compose rendering: passed;
- live frontend/backend health and encrypted Mailpit smoke tests: passed.

Automated test databases are disposable and fixture-built. The development
PostgreSQL database is persistent in its named volume. SQL dumps are reserved
for migration, backup/restore drills and reproducible incident snapshots, not
ordinary test initialization.

## Remaining engineering risks

### P0: research guarantees

1. Expand the typed immutable protocol rules beyond required tiers: tier
   hierarchy, linguistic types, controlled vocabularies, filename and media
   policies, participants, annotators, languages, alignment and overlap.
2. Complete the revision-scoped EAF projection for time slots, linguistic
   types, controlled vocabularies, languages/locales, properties, linked files,
   licenses, lexicon references and reference links.
3. Introduce an `AssetStore` boundary with filesystem and S3-compatible
   implementations. Keep immutable source objects authoritative and verify
   database/object consistency by checksum.
4. Design encrypted off-host backups and perform documented restoration drills
   before admitting identifiable data.
5. Move publication state from shared mutable Git worktrees to database-backed
   revisions and change sets. Git should become an idempotent export surface.

### P1: maintainability and assurance

- Split `service/git.py` (1,803 lines), `service/invitation.py` (1,057),
  `service/git_operations.py` (734), `service/user.py` (598), and `api/auth.py`
  (559) by explicit use case with typed results and domain errors.
- Decompose `ConfigureNamingStandards.vue` (2,371 lines),
  `ProfileOverview.vue` (2,251), and `RegisterPage.vue` (1,812) into feature
  composables, stores, forms and dialogs.
- Add API-level project-isolation, cookie/CSRF, upload, review and validation
  contract tests. Add concurrency tests for competing revisions and workers.
- Finish timezone-aware database constraints and project-scoped uniqueness
  constraints where the domain rules are already understood.
- Define handling and purge policy for permanently failed outbox records.

### P2: institutional readiness

- Data classification, consent/legal-basis metadata, withdrawal, retention and
  legal-hold procedures;
- metrics, alerts, storage-capacity monitoring, audit export, runbooks, RPO/RTO
  and incident response;
- managed production secrets, SMTP credentials, TLS termination and deployment
  hardening review;
- accessibility testing with researchers and a sanitized pilot corpus.

## Recommended next slice

Expand the now-working protocol snapshot incrementally, beginning with tier
hierarchy, linguistic types and controlled vocabularies. Add a focused protocol
editor page over the typed API, then migrate the existing naming-standard
configuration into draft snapshots without altering historical data. In
parallel, continue the revision-scoped EAF projection needed to evaluate those
rules. This grows the proven end-to-end boundary rather than introducing
unversioned checks elsewhere.
