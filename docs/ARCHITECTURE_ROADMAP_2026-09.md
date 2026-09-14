# ELANORA current architecture assessment and roadmap

**Assessment date:** 5 September 2026  
**Product stage:** hardened pre-production prototype

For the verified implementation status and objective-by-objective comparison,
see [`STATE_RECAP_2026-09-05.md`](STATE_RECAP_2026-09-05.md).

## Product boundary

ELANORA should be an institution-hosted collaboration and quality-governance
system around ELAN Annotation Format documents. It should not attempt to replace
the ELAN desktop editor. Researchers continue authoring time-aligned and
reference annotations in ELAN; ELANORA preserves submissions, validates them
against a published institutional protocol, coordinates review and concurrent
changes, and makes every accepted or rejected submission attributable and
recoverable.

The non-negotiable invariants are:

1. Exact submitted bytes are retained before parsing or transformation.
2. Published revisions are immutable and content-addressed.
3. A derived relational projection can always be rebuilt from source bytes.
4. A validation result identifies the validator and immutable protocol version.
5. One installation contains one institution; project access is default-deny.
6. Concurrent submissions never mutate a shared checkout underneath each other.
7. Deletion, retention, legal hold, backup and restoration are explicit states.

## What is good and should remain

- The modular-monolith deployment is appropriate for institution-operated
  installations. Microservices would add failure modes without product value.
- FastAPI, SQLAlchemy async, PostgreSQL 18, Alembic, Vue 3 and Vite are a sound
  technical baseline.
- Exact EAF bytes, SHA-256 identifiers, immutable `EAF_REVISION` rows and
  retained rejected-ingestion attempts correctly separate preservation from
  parsing success.
- The vendored XSD, hardened XML parser and explicit semantic checks are the
  right two-layer validation approach. XSD alone cannot express all ELAN
  editability rules.
- Institution IDs, project membership and centralized `ProjectGuard` establish
  a useful application authorization boundary.
- Tombstoning projects is safer than cascading away research history.
- Alembic startup migrations, guarded bootstrap, validated configuration and
  explicit development/test Compose projects make installations reproducible.
- The PostgreSQL integration suite now tests real migrations and dialect
  behavior; unit tests remain fast and independent.
- Keeping the legacy MySQL importer isolated, checksum-pinned and one-way is
  preferable to carrying two live database implementations.

## What needs refactoring

### P0 — preservation and consistency

`service/git.py` is about 1,800 lines and mixes workflow decisions, filesystem
mutation, Git commands, database writes, validation and rollback. Serialization
reduces races but does not make Git, PostgreSQL and filesystem updates atomic.
Replace this gradually with explicit use cases:

- `SubmitRevision`
- `ValidateRevision`
- `ProposeChangeSet`
- `ReviewChangeSet`
- `PublishRevision`
- `ExportGitHistory`

PostgreSQL should own workflow state. Original objects should be written
immutably first. A database transaction should append revision/change-set state
and an outbox job. Workers can then create derived projections and optional Git
exports idempotently. Git should become a compatibility/export surface, not the
transaction coordinator.

The current raw XML stored in PostgreSQL is a valid safety improvement, but it
will not scale to video and large institutional corpora. Introduce an
`AssetStore` port with filesystem and S3-compatible implementations. Store
object keys, checksums and retention state in PostgreSQL. Keep media out of Git
and normal database rows.

### P0 — protocol and validation versions

**Initial vertical slice completed 5 September 2026:** institution protocols,
draft and database-immutable published versions, project pinning, validator
release checksums, immutable validation runs/issues, audit events, a delegated
`manage_protocols` capability, and deterministic required-tier validation are
implemented. See [`PROTOCOL_GOVERNANCE.md`](PROTOCOL_GOVERNANCE.md). The
remaining work in this section is expansion and migration of the rule catalog.

Filename standards and accepted values are currently mutable configuration.
That makes it impossible to prove which exact rules accepted an old revision.
Introduce immutable `protocol_version`, `rule_definition`, `validator_release`
and `validation_run` records. Publishing a protocol freezes it; editing creates
a new draft version. Each validation issue needs a stable code, severity, XML
location and rule version.

Protocol rules should cover more than filenames: required tiers, tier parent
relationships, linguistic types and stereotypes, controlled vocabularies,
participants, annotators, languages, media-link policy, overlaps and time
alignment. Institution templates may be copied into projects, but a project
must pin the version it uses.

### P0 — EAF projection completeness

The current typed parser preserves the source and captures important annotation
relationships, but the searchable schema is still an incomplete projection of
EAF 3.0. Add revision-scoped tables or typed JSON projections for time slots,
linguistic types, controlled vocabularies and multilingual entries, locales,
languages, licenses, document properties, linked files, lexicon references and
reference-link sets. Every projected row must identify a document revision,
not merely a mutable file.

The original XML remains authoritative. Parser upgrades should create a new
projection version rather than changing research history.

### P1 — service and API boundaries

Several backend modules are too large: `invitation.py` exceeds 1,100 lines,
`git_operations.py` exceeds 700, `user.py` exceeds 600 and `auth.py` approaches
600. They contain repeated broad exception handling and dictionaries used as
implicit result types. Split by use case and replace stable dictionary contracts
with dataclasses or Pydantic models. Domain services should raise typed domain
errors; one API exception mapper should produce safe HTTP responses.

Authorization must also exist at the use-case boundary. Route dependencies are
helpful but insufficient if a service can later be called from a worker or CLI
without project context. Add negative tests for every mutation, including
cross-project IDs and filename collisions.

### P1 — frontend decomposition

Several Vue single-file components contain between 900 and 2,370 lines. In
particular, naming-standard configuration, profile overview and registration
mix API access, state transitions, validation, markup and extensive local CSS.
Extract feature composables, Pinia stores, request schemas, small dialogs and
shared form controls. Keep pages responsible for composition rather than domain
logic.

Two unused `ProjectUsersManager.vue` prototypes and their routed test page were
removed after reference analysis; `ConfigureProjectMembers.vue` is the active
implementation. Add component tests for review, conflict resolution, protocol
editing and upload error accessibility; the current frontend tests mostly
protect utilities and authentication recovery.

### P1 — installation and project constraints

The deployment, database and object store form the institution security
boundary. The database now permits one institution profile and assigns it a
stable installation UUID for provenance. Keep project authorization default-deny
and add database constraints for temporal validity, revision-local identities,
lifecycle transitions and uniqueness within project scope. Prefer UTC
`timestamptz` across all operational timestamps; several older models still use
naive `DateTime`.

Do not introduce same-database multi-tenancy or institution-level row security.
The current collaboration boundary is one installation: an externally affiliated
researcher may be invited, but receives a local account and local project
membership governed by the hosting institution.

Future cross-institution collaboration is not merely export/import. The project
owner's installation should remain the source of truth while remote researchers
authenticate through a federated identity, receive explicit project-scoped
grants, and access the project through the owner's API. Grants must be revocable,
audited and least-privilege. The product should then distinguish “shared with
me” remote projects from local projects and show owners which projects and
permissions are shared externally. Stable installation and remote-subject IDs,
origin metadata and immutable audit provenance belong in that protocol. Remote
identities must never gain direct database access. Signed exchange packages can
remain an offline or archival fallback, not the collaboration model itself.

Do not add constraints merely because PostgreSQL supports them. Overlap policy,
for example, depends on ELAN tier type and protocol rules and must be modeled
before a blanket exclusion constraint is introduced.

### P2 — operations and research governance

Implement encrypted off-host database and object backups, point-in-time recovery,
restore drills, metrics, structured audit export and storage-capacity alarms.
Define institutional RPO/RTO, retention schedules, participant withdrawal and
legal-hold procedures before identifiable corpora are admitted.

Existing-user invitations, account verification and password resets now use the
transactional PostgreSQL outbox and a separate worker. Verification and reset
secrets use authenticated encryption with explicit key identifiers; rotation
prepends a new key while retaining old keys until their events drain. Delivery
is at-least-once: providers or downstream consumers should use the event
identifier for idempotency where supported. Failed records remain inspectable
and retry up to the configured attempt ceiling so one poison message cannot
block the queue. Payloads are scrubbed after successful delivery; operations
still need a policy for reviewing and purging permanently failed records.
New-account invitations remain synchronous because their one-time bearer code
is not retained in a retry queue.

Treat videos, faces, voices and annotations as potentially sensitive research
data. Add data classification and consent or legal-basis metadata without
placing participant details in logs, branch names, object keys or Git commits.

## What can be removed or archived

Remove only after checking that no deployment still invokes them:

- Root ad-hoc MySQL-era repair scripts have been removed. Future diagnostics
  should be typed, read-only CLI commands with tests rather than hard-coded SQL.
- `docs/database/PROJECT-ELANORA_V2.ddl` through `V12.ddl` and the `.lun` design
  file are not schema sources. Move them under `docs/archive/database-design/`
  with a historical notice or remove them once preserved in Git history.
- `app/examples/logging_examples.py` should live in documentation or be removed;
  production packages should not carry untested example application code.
- Continue checking for unreferenced prototype views and components during each
  feature refactor; do not expose manual test harnesses as application routes.
- Retire compatibility environment loaders and deprecated CRUD wrappers only
  after callers have moved to `Settings` and typed repositories. Do not perform
  a blind deletion while the large service modules still depend on them.

Do not remove the legacy dump or importer yet. Freeze them as migration
artifacts and remove them only after every installation has been migrated,
reconciled, backed up and restore-tested.

## Testing strategy

- Unit tests: parser rules, filenames, protocol rules, semantic diff and pure
  domain transitions; no database.
- PostgreSQL integration tests: repositories, constraints, migrations,
  authorization queries, transaction boundaries and outbox idempotency.
- API tests: cookie, CSRF and session behavior, project isolation, uploads and
  stable validation-error contracts.
- Golden-corpus tests: sanitized valid, malformed, unfinished, legacy,
  multilingual-CV, unaligned and reference-annotation EAF documents.
- Concurrency tests: competing submissions from the same base revision and
  retrying workers.
- Recovery tests: restore a paired database and object snapshot and verify every
  revision checksum.

Opaque database dumps should not initialize automated tests. Each test creates
the minimum state it needs through fixtures or public use cases. Dumps remain
appropriate for backup, restore rehearsal and reproduction of an installation
state.

## Recommended delivery order

1. Keep CI and disposable PostgreSQL mandatory; add API login and upload tests.
2. Version protocols and attach immutable validation runs to revisions.
3. Complete the revision-scoped EAF projection and deterministic rebuild job.
4. Introduce object storage and paired backup/restore verification.
5. Replace shared-worktree Git workflows with change sets and outbox workers.
6. Split oversized backend services and frontend components along those use
   cases, removing duplicates as callers migrate.
7. Add database-enforced project and temporal invariants.
8. Complete privacy, accessibility and institutional operational review.
9. Pilot with a sanitized corpus before admitting identifiable media.

This sequence keeps the working prototype usable while moving the strongest
research guarantees into explicit, testable domain boundaries.

**Item 5 completed, 10 September 2026:** reviewed contribution publications now
create a durable PostgreSQL change set before execution. Publication is prepared
in an isolated Git worktree, guarded by the expected accepted revision, retried
by a dedicated worker, reconciled after an interrupted Git publication, and
exposed in the administrator operations status. Each project points explicitly
to its immutable PostgreSQL revision manifest; history and recovery resolve that
pointer rather than inferring accepted state from the current checkout. Git is a
checked compatibility export, and an administrator-confirmed recovery can
re-materialize it from the authoritative manifest. The unused direct Git commit
API was removed so it cannot bypass the revision ledger.

The next delivery target is item 6: split the oversized backend services and
frontend components by use case while preserving the tested public contracts.

**Item 6 progress, 10 September 2026:** accepted-history queries, safe Git export
identifier resolution, restoration preview, and restoration publication now live
in a dedicated `ProjectHistoryService`. Revision projection rebuilding,
integrity diagnosis and incident notifications, installation-wide scanning, and
administrator-confirmed manifest recovery now live in
`ProjectIntegrityService`. `GitService` retains thin compatibility delegates so
API and CLI callers do not change. Atomic empty-project creation and folder
import now live in a dedicated `ProjectLifecycleService`. Folder import builds a
hidden repository, publishes it at the canonical path, projects every EAF and
records the initial revision within one database transaction, and removes the
repository if projection or commit fails. The next slice is contribution intake;
contribution inspection should then be split from review and publication
decisions.

Contribution intake request validation, accepted-file detection, Git identity
setup, failed-branch cleanup, and API response construction now live in
`ContributionIntakeService`. It now also rejects submissions identical to the
accepted or an already-pending tree, analyzes and finalizes the review branch,
and records submission provenance in PostgreSQL. The remaining intake
orchestration is naming-policy lookup, file transfer and optional automatic
acceptance. Read-only EAF semantic summaries, changed-tier detection,
annotation-level comparison targets, and Git compatibility previews now live in
`ContributionInspectionService`. Queue presentation still composes these
results in `GitService`, while content-identity grouping and annotation-level
cross-contribution collision detection, protocol-version freshness, and
topic-versus-baseline scope evaluation now live with the inspection rules.
The stable administrator queue representation, including ready, duplicate,
superseded and inspection-error variants, now lives there as well. `GitService`
still coordinates the database query and per-item loop through compatibility
delegates. Administrator assignment of an existing research topic or explicit
approval of a distinct proposed topic now lives in `ContributionReviewService`;
it preserves the researcher's summary and derives a new topic's tiers from the
inspected contribution. Verified duplicate dismissal and terminal decline now
live there too, including audit records, contributor notifications, review-case
closure, reason validation and best-effort branch cleanup. The correction
lifecycle was already isolated in `ReviewService`. Final acceptance eligibility
now lives in `ContributionReviewService`, including supersession, unresolved
topic, open-review, EAF and pinned-protocol checks. Accepted contribution
publication now lives in `ContributionPublicationService`, which coordinates the
Git publication, relational projection, immutable revision ledger, audit event,
contributor notification, database rollback, Git rollback and backup refresh.
`GitService` retains a compatibility delegate while callers migrate. The next
item 6 slice is decomposing the contribution frontend by workflow and removing
the remaining presentation and request orchestration from its page component.

The contribution workspace tab navigation; queue summary, filtering, search and
ordering controls; contribution card header and permission-aware actions; and
research-context decision panel now live in focused Vue components with
component-level permission, accessibility and interaction tests. Collision
warnings, version history, duplicate and supersession evidence, quality checks,
file counts, semantic recaps and conflicted filenames now live in a tested card
body component as well. Project-scoped contribution loading, stale-project race
protection, proposed-topic initialization, review counts, research-topic loading
and read-side error state now live in `useContributionQueueData`. Topic
classification, compatibility testing, merge confirmation and publication,
duplicate dismissal, terminal decline, busy states and API-error presentation
now live in `useContributionMutations`, with services and confirmation UI
injected for direct testing. The page retains route/workspace navigation and the
decline dialog itself. The contribution page decomposition is now sufficiently
split by use case; the next item 6 target is the next oversized component chosen
by risk and test coverage rather than further fragmenting this page.

`ReviewCasePanel` is the next risk-selected target. Its active-review summary,
empty/loading/error states and responsive queue controls now live in
`ReviewQueueOverview`; active versus archived grouping, nested correction search,
state filtering and bounded pagination now live in `useReviewCaseQueue`. Both
boundaries have direct tests. Correction-request draft state, large-file search
and pagination, per-file change selection, validation, reset behavior and API
payload construction now live in `useReviewCaseDraft`, with direct tests for the
multi-change and legacy question workflows. Reviewer task decisions and
revision-transition orchestration are the next slices.
