# ELANORA repository cleanup audit

**Audited:** 5 September 2026  
**Scope:** current repository, live development Compose stack, runtime storage,
tracked historical artifacts, application modules, tests, and deployment files

## Executive result

ELANORA should be refactored progressively, not restarted. Its current modular
monolith, PostgreSQL, FastAPI, Vue, immutable EAF source revisions, project
authorization, protocol snapshots, and browser bootstrap are the right base.
The complete repository gate passes.

The repository is nevertheless carrying three generations at once:

1. historical database designs and static HTML prototypes;
2. the original Git- and mutable-projection application;
3. the newer revision-, protocol-, and PostgreSQL-oriented architecture.

The next cleanup should remove generation 1, isolate the migration-only pieces
of generation 2, and progressively move active workflows to generation 3. A
large deletion without those boundaries would risk deleting migration evidence
or relational data that the current service layer still reads.

## Changes completed during this audit

- The live host project path was confirmed as
  `website/data/elanora_projects`; Compose bind-mounts it at
  `/app/website/data/elanora_projects`.
- Development storage initialization now repairs ownership recursively rather
  than only changing empty parent directories.
- The current `lsfb`, `frapé`, `test`, and `testttt2` repositories were repaired
  to the configured development UID and GID. The backend can write their
  directories and Git indexes.
- Production and server storage initialization now recursively assigns runtime
  data to the non-root application UID (`10001`) as well.
- Git commands trust only their resolved project directory per invocation,
  report failures, and preserve Unicode paths rather than changing global Git
  configuration.

## Verified baseline

The complete `make check` gate passed:

- Ruff formatting and lint: 239 backend files;
- mypy: 27 strict architectural source files;
- backend unit tests: 60 passed;
- PostgreSQL integration tests: 30 passed from an empty database through all
  nine Alembic migrations;
- frontend ESLint, Stylelint, and Prettier: passed;
- frontend tests: 28 passed across 10 files;
- production frontend build: passed.

This is a reliable regression baseline, but frontend workflow coverage is still
small compared with 193 Vue/JavaScript source files. The strict mypy boundary
also covers only the new architectural core, not the large legacy services.

## Keep and continue

- `website/backend/app/elan`, the vendored EAF schema, immutable revision
  records, ingestion attempts, hashes, and structured validation issues;
- PostgreSQL, SQLAlchemy models, Alembic migrations, and the disposable
  PostgreSQL integration stack;
- centralized project authorization and the documented authorization matrix;
- one installation per institution, browser bootstrap, and the maintained CLI
  bootstrap/recovery commands;
- protocol drafts, immutable published versions, project pinning, validator
  releases, and validation evidence;
- transactional email outbox and Mailpit development catcher;
- `website/static` while the one-way legacy migration still needs its sanitized
  source corpus;
- the recovery cache until verified encrypted off-host backup and restoration
  exist. It is not itself a sufficient backup.

## Confirmed removable source-tree artifacts

These have no runtime references and are preserved by Git history:

- `deploy/README.md` and the otherwise empty `deploy` directory;
- empty placeholder READMEs under backend/frontend `docker`, `tests`,
  `src/utils`, and `website/static` where they document nothing;
- `docs/prototype`: the old standalone HTML/CSS/JavaScript mock application,
  superseded by the Vue application;
- `docs/database/PROJECT-ELANORA_V2.ddl` through `V12.ddl`, the `.lun` model,
  and `datagrip_ddl`: historical MySQL-era designs that are not schema sources;
- `website/scripts/start.sh` and `start.bat`: superseded by the root Makefile,
  contain obsolete Docker Desktop assumptions, and run mutation such as
  `npm audit fix` during startup;
- root `elanora_projects/.githooks/post-receive` and the empty root
  `.elanora_projects_backups` directory. The hook is outside the live data
  path, targets obsolete port `8000`, calls a removed endpoint, and is not
  installed into current projects;
- the ignored empty `website/backend/website/database/dump.sql` directory tree;
- generated `website/frontend/dist`, caches, coverage output, and other ignored
  build products whenever local disk cleanup is desired.

The Python `installer/setup_instance.py` and two `run_setup_instance` wrappers
are also technically redundant: the browser setup is primary and
`elanora-bootstrap` is the maintained automation/recovery CLI. They can be
removed if no external deployment documentation or operator still invokes the
old path.

## Conditional domain removal

The following tables/models are present in the initial migration but have no
active API/UI workflow. The development database contains zero rows in each:

- `COMMENT`, `COMMENT_PROJECT`, `COMMENT_ELAN_FILE`, `COMMENT_CONFLICT`;
- `ANNOTATION_STANDARD`, `PROJECT_ANNOT_STANDARD`;
- `CONFLICT`, `CONFLICT_OF_ELAN_FILE`, `USER_WORK_ON_CONFLICT`.

They should not simply disappear from Python imports. If their product concepts
are rejected, add one reviewed Alembic migration that drops their foreign keys,
tables, models, CRUD modules, enums, relationships, and notification remnants.
If comments or durable conflict assignments are planned, keep and redesign them
against immutable revisions/change sets instead of the current orphan schema.

Postal addresses are active but questionable for this product. Registration
and profile editing duplicate substantial validation logic and send typed
address input directly from the browser to third-party Rest Countries and
Nominatim services. This adds privacy disclosure/consent obligations, external
availability and rate-limit dependencies, and roughly 4,600 lines across the
registration/profile surfaces. Unless postal addresses have a real research or
institutional requirement, removing them is preferable data minimization.

## Highest-value refactors

### 1. Finish the preservation model

Original EAF bytes are now immutable, but the searchable relational projection
is incomplete. Add revision-scoped time slots, linguistic types, controlled
vocabularies/multilingual entries, languages/locales, properties, licenses,
linked files, lexicon references, and reference-link sets. Projections must be
rebuildable and versioned by parser release.

Introduce an `AssetStore` interface with filesystem and S3-compatible
implementations. Keep large media outside PostgreSQL and Git; store immutable
object keys, checksums, sizes, MIME evidence, and retention state in PostgreSQL.

### 2. Replace Git as workflow coordinator

`app/service/git.py` is now about 2,000 lines and still combines filesystem,
Git, database, validation, contribution, rename, and recovery workflows. Locks
reduce races but cannot make those systems transactional. Split it into typed
use cases such as `SubmitRevision`, `ReviewChangeSet`, `PublishRevision`,
`RecoverProjection`, and `ExportGitHistory`. PostgreSQL should own workflow
state; Git should be an idempotent compatibility/export surface.

Until that migration is complete, every cross-system operation must use the
existing operation journal/evidence pattern and remain recoverable after any
intermediate failure.

### 3. Decompose oversized modules

Backend priorities:

- `service/git.py` (~2,000 lines);
- `service/invitation.py` (~1,057 lines);
- `service/git_operations.py` (~798 lines);
- `api/git.py` (~650 lines);
- `service/user.py` (~598 lines);
- `api/auth.py` (~559 lines).

Frontend priorities:

- `ConfigureNamingStandards.vue` (~2,371 lines);
- `ProfileOverview.vue` (~2,251 lines);
- `RegisterPage.vue` (~1,812 lines);
- `ConfigureProjectMembers.vue` (~1,050 lines);
- `ProjectsPage.vue` (~962 lines);
- `UploadFolder.vue` (~881 lines);
- `ConfigureEffectiveStandards.vue` (~873 lines);
- `ProjectSyncDialog.vue` (~863 lines).

Pages should compose feature components. API calls and cancellable request
state belong in feature composables/stores. Stable backend results should use
Pydantic models/dataclasses and typed domain errors, with one HTTP error mapper.

### 4. Remove duplicated infrastructure and UI logic

- Build production and server Compose files from a documented common base plus
  small overrides. They currently duplicate services, health checks, mounts,
  storage initialization, database settings, and worker configuration.
- Centralize the three backend `CryptContext` instances behind one password/token
  hashing service and finish the bcrypt/passlib compatibility cleanup.
- Extract registration/profile address fields and validation if addresses stay.
- Consolidate project-scoped async loading into one stale-request-safe
  composable rather than implementing watchers and counters independently.
- Move recurring dialog, button, form, state-panel, and notification patterns
  into the design system. Do not create a generic component unless at least two
  real callers share its behavior.
- Replace development `console.log` traces in authentication, rename, standard,
  and notification flows with a small environment-aware client logger; never
  log email addresses, tokens, annotation content, or participant metadata.

### 5. Improve performance and request ownership

- Project file loading currently fans out across file listing, multiple standard
  requests, and media-standard requests. Add a typed project-workspace summary
  endpoint or project-keyed query cache to avoid duplicate round trips.
- The naming-standard store holds mutable global results; make caches explicitly
  project-keyed so late responses cannot contaminate another project.
- Replace notification polling with visibility-aware backoff now, and consider
  server-sent events only when the operational cost is justified.
- Profile and registration address validation perform repeated third-party
  requests. If retained, proxy/cache them server-side with explicit timeouts,
  quotas, privacy documentation, and graceful manual-entry fallback.
- Add measurement budgets for API latency, query counts, main bundle size, and
  route chunks before further visual optimization.

## Correctness, security, and operational work still required

- Add negative API tests for every project mutation, not only representative
  authorization routes.
- Add end-to-end browser tests for setup, login recovery, project switching,
  EAF upload/rejection, contribution review, protocol publication, and server
  recovery.
- Add concurrency/failure-injection tests around competing submissions and
  every filesystem/Git/database boundary.
- Expand mypy incrementally to each service when it is decomposed; do not mark
  the 2,000-line legacy modules strict without first introducing typed seams.
- Complete timezone-aware columns and database constraints where the domain
  rules are known.
- Define retention and purge behavior for rejected uploads, failed outbox
  events, tombstoned projects, revisions, media, audit logs, and legal holds.
- Implement encrypted off-host backups, paired database/object snapshots,
  checksum reconciliation, restoration drills, RPO/RTO, monitoring, capacity
  alarms, and incident runbooks before identifiable research data is hosted.
- Perform a DPIA/privacy and accessibility review with the institution and Deaf
  researchers. Videos, faces, voices, and free-text annotations may be highly
  sensitive research data.
- Design federation later around stable installation identity, remote subjects,
  explicit project grants, revocation, audit, and the owner's API as source of
  truth. Do not introduce shared-database multi-tenancy now.

## Recommended delivery sequence

1. Remove confirmed historical/dead artifacts and decide the four conditional
   product questions below.
2. Remove rejected domain tables through an Alembic migration and associated
   code/tests.
3. Decompose project workspace loading and `git.py` around typed use cases while
   preserving behavior with characterization tests.
4. Complete revision-scoped EAF projections and protocol rules together.
5. Add `AssetStore`, immutable media objects, and verified off-host recovery.
6. Replace Git-coordinated publication with database revisions/change sets.
7. Complete privacy, accessibility, operations, and sanitized pilot testing.

## Decisions requested

## Decisions recorded on 5 September 2026

- Confirmed historical artifacts were approved for removal and have been
  deleted.
- The legacy installer and launch wrappers were retired. Browser setup and the
  maintained `elanora-bootstrap` CLI are the supported paths.
- Postal address collection remains a product requirement for now.
- Collaborative comments and durable assignment were confirmed. The orphan
  legacy schema has been replaced by revision-scoped review cases; see
  [`EAF_REVIEW_WORKFLOW.md`](EAF_REVIEW_WORKFLOW.md).

The questions below are retained as the decision record.

Reply with four compact answers, for example `1 yes, 2 remove, 3 remove, 4 no`:

1. **Historical cleanup:** delete all confirmed removable tracked artifacts
   listed above now? Recommended: **yes**.
2. **Installer compatibility:** keep the old Python wrapper and shell/batch
   launchers, or expose only browser setup plus `elanora-bootstrap`?
   Recommended: **remove wrappers**.
3. **Postal addresses:** does ELANORA have a real requirement to collect a
   researcher's complete street address? Recommended: **remove address
   collection and third-party browser validation**.
4. **Comments/conflict assignments:** are collaborative comments and durable
   assignment of conflicts planned in the next product phases? Recommended:
   **keep the concept only if planned; otherwise remove the unused schema now**.
