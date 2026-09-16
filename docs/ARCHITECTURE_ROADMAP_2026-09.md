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

**Decided 16 September 2026:** ELANORA manages projects and EAF documents;
researchers never upload video or audio into it, and media stays on
institutional storage referenced by the EAF. Exact EAF bytes therefore remain
in PostgreSQL, which suits small XML documents, protected by verified off-host
backups. The earlier plan for a separate media object store is withdrawn; the
existing asset storage remains for instance branding only.

### P0 — protocol and validation versions

**Initial vertical slice completed 5 September 2026:** institution protocols,
draft and database-immutable published versions, project pinning, validator
release checksums, immutable validation runs/issues, audit events, a delegated
`manage_protocols` capability, and deterministic required-tier validation are
implemented. See [`PROTOCOL_GOVERNANCE.md`](PROTOCOL_GOVERNANCE.md). The
remaining work in this section is expansion and migration of the rule catalog.

**Rule catalog completed 15 September 2026:** every rule takes an error or
warning severity (warnings are recorded and shown to reviewers but never
block); vocabulary, tier metadata, completeness, linguistic-type constraint and
frozen filename-standard rules are evaluated under validator release 3; the
protocol editor covers every family; and `elanora-copy-naming-standards` copies
each project's upload naming standard into a draft for review. While a pinned
protocol carries a filename standard, the legacy upload naming setting is not
consulted. Overlaps are already refused by semantic EAF validation for every
file. Running the copy command on production data is an operator step.

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

**Completed 15 September 2026:** revision manifests now store projection
version 2, which gives every element type of the vendored EAF 3.0 schema a typed
shape: licences, linked files, properties, linguistic types, locales, languages,
constraints, controlled vocabularies with their descriptions and entries per
language, lexicon references, external references, and reference-link sets with
their cross and group links. Space-separated `IDREFS` attributes become lists.
Each element keeps a map of any attribute without a dedicated field, so typed
fields and that map together account for the whole source. A test using a
fixture that exercises every element type checks that no attribute value or
text is left out. Version 1 omitted lexicon references and stored the rest as
serialized XML snippets. Manifest rows stay append-only;
`revision_projection()` re-derives older rows from their stored bytes on read,
and returns the stored projection if current validation would refuse a
historical source.

Building that fixture exposed two validator defects that refused valid ELAN
files at upload: an annotation citing several external references, and
`TIME_ALIGNABLE="1"`, which `xsd:boolean` defines as true.

Queryable projections are stored per revision as JSON. Relational tables for
this metadata are not yet warranted; they should follow the protocol rules that
need to query it.


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

**Split completed 16 September 2026:** every oversized backend module is now
divided by use case, each keeping the import surface its callers already use:

| Was | Now |
| --- | --- |
| `service/invitation.py`, 887 lines | issuing, decisions, queries, notifications |
| `service/user.py`, 743 lines | sessions, registration, verification, passwords, profile, account status, errors, and one shared password hashing context |
| `service/git_operations.py`, 971 lines | command runner, branches, merge, uploads, results, and one backup hook |
| `service/protocol.py`, 1008 lines | administration, capabilities, validation runs, compliance, suggestions, shared reads, errors |
| `api/v1/git.py`, 1163 lines and 32 routes | projects, contributions, history, synchronization, renames, with shared services in `git_shared` |
| `api/v1/auth.py`, 601 lines and 10 routes | sessions, registration, recovery |

Route inventories were compared before and after, so no path or method changed.
Guardrail tests that read a named source file now read the module that holds the
code, rather than a re-export that holds none. What remains here is replacing
the dictionaries still used as implicit result types with typed models, and
raising typed domain errors so one API mapper produces safe HTTP responses.

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

**Reviewed 16 September 2026:** every operational timestamp is now UTC
`timestamptz`, enforced by guardrail tests. Lifecycle, uniqueness and
non-negative interval constraints already exist for revisions, protocol
versions, reviews, change sets, scans and sync operations. Ordering constraints
between timestamps written by different clocks (the application server and
PostgreSQL) were deliberately not added: ordinary clock skew would reject valid
writes.

Do not add constraints merely because PostgreSQL supports them. Overlap policy,
for example, depends on ELAN tier type and protocol rules and must be modeled
before a blanket exclusion constraint is introduced.

### P2 — operations and research governance

**Decided 16 September 2026:**

- *Classification:* each project records a data classification (public,
  internal, confidential, sensitive personal data) and its legal basis or
  consent reference. This is record-keeping for retention timing and
  compliance evidence only. It must never restrict a project member's access,
  export, or visibility: every researcher granted a project needs full ability
  to export and reuse its EAF files, and gating that would defeat the product.
- *Retention:* deleting a project leaves a tombstone; its content is purged once
  the project's retention period ends unless a legal hold is set. Participant
  withdrawal is deliberately **not** automated: ELANORA has no reliable
  participant identity (the EAF `PARTICIPANT` tier attribute is free text an
  annotator types, not a controlled identifier), so matching a withdrawal
  request to "all of this person's data" cannot be done safely by software.
  It is a rare, manual, admin-only action: an administrator locates the
  relevant file(s) and edits or removes the content, recorded as an audit
  event with the existing tooling. Every deletion-adjacent action (project
  deletion, governance settings, the retention purge itself) already requires
  project-admin permission or runs as an unattended scheduled job outside any
  interactive user's reach; a contributor has no path to delete accepted
  content or their own submitted data.
- *Recovery targets:* at most 24 hours of data loss and restoration within one
  day, met by nightly encrypted off-host backups of the database and project
  storage, with a scheduled restore drill.

Implement encrypted off-host backups, restore drills, metrics, structured audit
export and storage-capacity alarms to meet those targets before identifiable
corpora are admitted.

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

**Item 1 completed, 16 September 2026:** HTTP tests drive the real
application, middleware included, with a database session per request and
cookies that follow their paths. They cover sign-in cookies and flags, uniform
login failures, CSRF enforcement, refresh rotation and sign-out, a contribution
from project creation through upload, acceptance and protocol validation,
requested changes answered by a correction, declining, protocol administration
and delegation, and uploads by outsiders and anonymous visitors. They found
three defects, now fixed: sign-out never revoked the refresh session because
the refresh cookie's path excluded the sign-out endpoint; creating a protocol
or draft version returned a server error after saving it; and two uploads by
one person within a second failed, with the cleanup deleting the earlier
contribution's branch. Separately, the server's filename matcher refused every
filename whenever a naming standard was set.

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
`GitService` retains a compatibility delegate while callers migrate.

**Item 6 progress, 15 September 2026:** file renaming now lives in
`FileRenameService`, upload naming-standard enforcement in
`upload_naming_compliance`, and folder reconciliation in
`ProjectFilesystemSyncService`. `GitService` is down from about 1,700 to about
1,070 lines and delegates to each. Three defects surfaced while writing the
tests these paths had been missing. A bulk rename that failed while committing
rolled back the database but left its filesystem renames applied; renames are
now reversed together. `GitCommandRunner.commit` returns nothing, so both
rename responses reported success with a null commit hash; the hash is now read
back. A non-compliant filename was reported to the researcher as a server data
issue because the specific error was raised inside the handler that replaced
it; resolving the standard and judging a filename are now separate, and the
latter surfaces as a 422 naming the file and expected pattern. Applying and
previewing a synchronization also each carried their own copy of the same Git
status reading, so an approved preview could drift from the batch that ran;
both now share one reading.

Later the same day the review queue moved to `ContributionQueueService`,
researcher submission to `ContributionSubmissionService`, project rename and
delete into `ProjectLifecycleService`, and missing-storage recovery to
`ProjectRecoveryService`. An unused merge path that bypassed the revision ledger
was removed. `GitService` is now about 685 lines, and what remains is largely
read-only listing and delegates. Each extraction added the tests its path had
been missing, and each surfaced real defects:

- One unreadable contribution failed the whole review queue, hiding every
  other contribution from administrators.
- A failed automatic acceptance reported a saved contribution as a failed
  upload.
- A project rename moved its folder before its record and could not undo it;
  reusing a deleted project's name also moved live files into the folder a
  restore of that project writes to.
- Restoring a live project with missing storage always failed, restoring over
  intact storage rolled back accepted history, and deleting such a project
  removed its last backup before recording the deletion.
- Code throughout assumed the working tree is on the accepted branch. After an
  interrupted upload, publication wrote the wrong parent into the immutable
  ledger, renames and synchronization committed onto a stray branch, and
  integrity recovery reset the stray branch while reporting success.
  `GitCommandRunner.canonical_head()` and `ensure_canonical_checkout()` now
  enforce the invariant on every write and provenance read.

**Concurrency, 15 September 2026:** the row locks protecting research data now
have tests that force real contention against PostgreSQL. A blocker holds the
contended lock until every worker is confirmed waiting on it. Each test fails
when its lock is removed. They found that suspending administrators could
deadlock, and that the cross-process project write lock could leak until
restart when acquire and release ran on different threads.

A projected EAF is now identified by its filename within a project (migration
0033). The inherited uniqueness on content made two distinct files with identical
bytes, such as sessions started from one template, impossible to publish. The
administrator branch-checkout endpoint was also removed, following the August
audit's decision never to switch a shared checkout from an HTTP request.

**Contribution frontend, 15 September 2026:** `PendingUploadPage` now only
composes components and handles events; its script fell from 414 to 250 lines.
Queue grouping and filtering live in `useContributionQueueView`, polling in
`useContributionQueueRefresh`, URL-driven workspace state in
`useContributionWorkspace`, the decline dialog in `ContributionDeclineDialog`,
and the conflict decision in `useResolutionDecision`. The page, the resolution
view and the annotation comparison previously had no tests. Writing them found:

- a workspace whose contribution was accepted elsewhere left the page without
  its tabs;
- the corrections card counted a different set than its filter showed;
- automatic refresh reloaded contributions but not the review cases their status
  comes from;
- the resolution confirmation omitted that other files, deletions included, are
  applied either way, stated an annotation impact counted only from files
  already opened, and could carry an acknowledged decision to another
  contribution;
- a slow comparison response could be shown, and recorded by that decision, as
  another file's comparison.

The decline dialog, workspace and resolution views are translated, with
`contributionResolution` added to the parity check.

Item 6 is otherwise complete. **Translation completed 16 September 2026:**
`ReviewCasePanel` (with `ReviewQueueOverview` and the reviewer decision and
transition composables), `AcceptedProjectHistory`, `ConflictMergeView` and
`ArchivedReviewList` now render French and Japanese through the protected
`reviewCases`, `acceptedHistory`, `annotationComparison` and `reviewArchive`
namespaces. The i18n setup also passed an unknown `fallbackLanguage` option, so
untranslated strings showed raw keys; it now uses `fallbackLocale`.

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
multi-change and legacy question workflows. Reviewer task selection, legacy
reopened-task recovery, annotation-level revision targets, approval requests,
busy/error state and outcome messaging now live in
`useReviewerTaskDecisions`, with direct tests for partial and final decisions.
Confirmed review-state transitions, structured follow-up revision requests,
reviewer assignment and corrected-upload linking now live in
`useReviewCaseTransitions`. Its direct tests cover cancellation, payload and
feedback construction, cleanup, assignment normalization and API failures. The
remaining `ReviewCasePanel` work can now be selected by presentation size rather
than untested workflow risk.

The next size-and-risk assessment selected `ConfigureNamingStandards`, the
largest remaining frontend component and one without a direct test boundary.
Numeric accepted-value normalization, pattern-component extraction,
separator-aware block parsing, example character grouping and regex-specific
field guidance now live in `namingStandardPattern` with direct edge-case tests.
Example-to-regex inference now uses that same tested boundary, including
interactive division of ambiguous character runs, Unicode-aware prefix
detection, numeric-range prompts and explicit cancellation errors. Separator
detection ignores separator characters inside component braces, fixing
hyphenated patterns whose `prefix_*` component previously caused the underscore
to be selected. Cross-project naming-standard import state and requests now live
in `useNamingStandardImport`, including source project loading, source file-type
recovery, folded selection state, refresh and translated outcomes. Duplicate
filtering now compares the stable underlying file type instead of unrelated
project-local file-type row IDs. `NamingStandardImportDialog` now owns the
responsive, keyboard-dismissible import presentation with direct tests for its
dialog semantics, duplicate filtering, missing-file-type recovery and immutable
selection events. The final action appears only at the applicable selection
step. `NamingStandardList` now owns accessible standard disclosure controls,
responsive pattern evidence and horizontally safe component tables, with direct
interaction tests. The create form is the last substantial naming-standard
presentation boundary before reassessing the next oversized feature.
