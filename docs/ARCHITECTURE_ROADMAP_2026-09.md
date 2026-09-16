# ELANORA architecture and roadmap

**Last updated:** 16 September 2026
**Product stage:** hardened pre-production prototype, distributed to
institutions that install and operate it themselves

This document states what ELANORA is, what is already true of it, and what
remains. The history of how each part got here is condensed at the end.

## Product boundary

ELANORA is an institution-hosted collaboration and quality-governance system
around ELAN Annotation Format (EAF) documents. It does not replace the ELAN
desktop editor: researchers author annotations in ELAN, and ELANORA preserves
their submissions, validates them against a published institutional protocol,
coordinates review and concurrent changes, and makes every accepted or rejected
submission attributable and recoverable.

It manages projects and EAF files only. Researchers never upload video or
audio; media stays on institutional storage referenced by the EAF.

The non-negotiable invariants:

1. Exact submitted bytes are retained before parsing or transformation.
2. Published revisions are immutable and content-addressed.
3. A derived relational projection can always be rebuilt from source bytes.
4. A validation result identifies the validator and immutable protocol version.
5. One installation contains one institution; project access is default-deny.
6. Concurrent submissions never mutate a shared checkout underneath each other.
7. Deletion, retention, legal hold, backup and restoration are explicit states.

## Status at a glance

| # | Delivery item | Status |
| --- | --- | --- |
| 1 | CI, disposable PostgreSQL, API login and upload tests | Done |
| 2 | Versioned protocols with immutable validation runs | Done |
| 3 | Revision-scoped EAF projection and deterministic rebuild | Done |
| 4 | Separate object storage for media | Withdrawn: no media is stored |
| 5 | Change sets and outbox workers instead of shared-worktree Git | Done |
| 6 | Split oversized backend services and frontend components | Backend done; frontend in progress |
| 7 | Database-enforced project and temporal invariants | Done |
| 8 | Privacy, operations and self-maintenance for institutions | Done |
| 9 | Accessibility review and sanitized pilot corpus | Open; needs people and data, not code |

Quality gates on every change: `make check` runs the credential scan; ruff,
mypy, 670 backend unit tests, 214 PostgreSQL integration tests with a
downgrade/upgrade and `alembic check`, and the recovery drill; then eslint,
stylelint, prettier, the three-language translation parity check, 388 frontend
tests and the production build. The database is at migration 0037.

## What is in place

### Architecture

- A modular monolith: FastAPI, SQLAlchemy async, PostgreSQL 18 and Alembic
  behind a Vue 3 and Vite interface. Microservices would add failure modes
  without product value for a single-institution installation.
- PostgreSQL owns workflow state. Exact EAF bytes, SHA-256 identifiers,
  immutable `EAF_REVISION` rows and retained rejected-ingestion attempts
  separate preservation from parsing success. Git is a checked compatibility
  export that can be re-materialized from the revision ledger.
- Contribution work is split by use case: intake, inspection, review,
  publication, queue, submission, file renaming, filesystem synchronization,
  project history, integrity, lifecycle and recovery each have a service.
  Publications run through durable change sets retried by a worker.
- Two validation layers: the vendored ELAN 3.0 XSD and ELANORA's semantic and
  cross-reference checks, followed by the pinned protocol.

### Protocols and projection

- Institution protocols have drafts and database-immutable published versions.
  Projects pin a version; validation runs and issues are immutable and name the
  validator release. Rules cover required tiers and parents, linguistic types
  and constraint stereotypes, controlled vocabularies and their languages,
  participants, annotators, tier languages, completeness, time alignment,
  linked media and a frozen filename standard, each as an error or a warning.
- Revision manifests store projection version 2, which gives every element of
  the EAF 3.0 schema a typed shape and accounts for every attribute and text.
  Older manifests are re-derived from their bytes on read.

### Authorization, accounts and security

- Project access is default-deny through `ProjectGuard` and delegated
  capabilities; negative tests cover mutations across projects.
- Sessions use HTTP-only cookies, CSRF protection, rotating refresh sessions
  revoked on sign-out, suspension and password change.
- Passwords follow NIST SP 800-63B revision 4: at least 15 characters, no
  composition rules, and refusal of repetitive patterns, passwords built from
  the account's own details, and passwords found in breaches through the Have I
  Been Pwned range API with k-anonymity. See
  [`PASSWORD_POLICY.md`](PASSWORD_POLICY.md).
- Every refusal the API returns carries a stable code from
  `app/core/errors.py`; the interface translates it. Messages never contain
  tokens, passwords, participant data or internal exception text.
- Verification and password reset do not reveal whether an address has an
  account.

### Operations, for installations nobody staffs

- `installer/install.sh` installs an institution from three answers and is safe
  to re-run; `elanora-setup` generates every secret and never rotates one.
- A `maintenance-worker` backs up daily, verifies weekly, applies retention
  daily and watches disk capacity hourly, deciding what is due from runs
  recorded in PostgreSQL. The operations page reports what actually happened.
- Emails go through a transactional outbox with encrypted payloads and bounded
  retries, rendered from shipped templates with every value escaped.
- `elanora-export-audit` answers a compliance request from the audit trail.
- Recovery targets: at most 24 hours of data loss and restoration within a day,
  met by encrypted backups and a tested restore drill
  ([`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md)).

### Research governance

Each project records a data classification, its legal basis or consent
reference, a retention period and an optional legal hold
([`DATA_RETENTION.md`](DATA_RETENTION.md)). Two decisions constrain this:

- Classification is record-keeping for retention timing and compliance
  evidence only. It never restricts a member's access, export or visibility:
  researchers granted a project need to export and reuse its EAF files.
- Participant withdrawal is not automated. ELANORA has no reliable participant
  identity (the EAF `PARTICIPANT` attribute is free text), so an administrator
  locates and edits the affected files by hand, recorded in the audit trail.

### Interface

- English, French and Japanese are complete; the parity check covers every key
  in both directions. The setup, home, protocol, contribution, registration
  and profile screens, all dialogs and all API errors are translated.
- Registration is composed from tested composables and field components, and
  shares its field and password rules with the profile editors.
- Every icon the interface names is registered; a test enforces it.
- Confirmation dialogs state their tone explicitly rather than guessing it from
  English words.

## What remains

### Frontend decomposition (item 6)

Components still over about 800 lines, largest first:

| Component | Lines | Notes |
| --- | --- | --- |
| `common/ReviewCasePanel.vue` | 2,582 | Workflows already live in tested composables; the template and styles remain. |
| `views/TiersPage.vue` | 1,294 | Research topics, tier browsing and export in one page. |
| `projectConfiguration/ConfigureProjectMembers.vue` | 1,120 | Member list, permission editing and capability grants. |
| `projectConfiguration/ConfigureProtocols.vue` | 1,061 | Protocol list, editor and compliance scan panel. |
| `common/UploadDetailsView.vue` | 944 | |
| `views/ProjectsPage.vue` | 920 | |
| `common/UploadFolder.vue` | 887 | |
| `common/ConflictMergeView.vue` | 860 | |
| `projectsPage/ProjectSyncDialog.vue` | 856 | |
| `common/UploadResolutionView.vue` | 853 | |

The approach that worked for registration and contributions: move state and
requests into composables with direct tests, move self-contained markup into
components, keep pages responsible for composition, and translate anything
found in English along the way.

### Backend typing

`mypy.ini` checks an explicit list of modules strictly. The module splits moved
code into new files that are not on that list, and several services still
return anonymous dictionaries where CONTRIBUTING.md asks for typed contracts.
Strict mypy over the whole `app` package currently reports 108 errors in 22
files, so the goal is to make the whole package strict and replace the
remaining result dictionaries with dataclasses or Pydantic models.

### Smaller items

- The legacy MySQL dump and importer stay frozen until every installation has
  been migrated, reconciled, backed up and restore-tested.
- About 950 lines of small repeated CSS rules remain across component styles;
  consolidating them needs visual review.
- EAF validation issue messages come from the validator in English; the issue
  codes could be translated the way API errors are.

### Item 9: before identifiable corpora are admitted

Not software: an accessibility review with Deaf and disabled researchers, and a
pilot with a sanitized corpus.

### Future: cross-institution collaboration

The owner's installation should remain the source of truth while remote
researchers authenticate through a federated identity, receive explicit,
revocable, audited project-scoped grants, and work through the owner's API.
Remote identities never gain database access. Signed exchange packages can be
an offline or archival fallback, not the collaboration model. Same-database
multi-tenancy and institution-level row security are out of scope.

## Testing strategy

- **Unit:** parser rules, filenames, protocol rules, semantic diff, pure domain
  transitions and error contracts; no database.
- **PostgreSQL integration:** repositories, constraints, migrations,
  authorization queries, transaction boundaries and outbox idempotency.
- **HTTP:** the real application with its middleware — cookies, CSRF, sessions,
  project isolation, uploads and error contracts.
- **Concurrency:** real contention against PostgreSQL; each test fails when its
  lock is removed.
- **Recovery:** restore a paired database and storage snapshot and verify every
  revision checksum.
- **Frontend:** composables and components tested directly, pages mounted with
  the real English messages.

Each test creates the state it needs through fixtures or public use cases;
opaque database dumps are for backup and restore rehearsal, not test setup.
Every fixed defect gets a test, and new guards are checked by reintroducing the
defect.

## History

Dates are 2026.

- **5 September.** Protocol governance vertical slice: drafts, immutable
  published versions, project pinning, validator releases, immutable
  validation runs and a delegated capability.
- **10 September.** Item 5: reviewed publications become durable change sets
  prepared in isolated worktrees, retried by a worker and reconciled after
  interruption; history and recovery resolve the immutable manifest pointer.
  Project history, integrity and lifecycle services extracted from `GitService`.
- **15 September.** Protocol rule catalog completed with error and warning
  severities. EAF projection version 2. Contribution intake, inspection,
  review, publication, queue, submission, renaming, synchronization and
  recovery extracted; `GitService` fell from about 1,800 to about 630 lines.
  Concurrency tests against real PostgreSQL. The contribution page decomposed
  into tested composables and components. Defects found and fixed included an
  unreadable contribution hiding the whole review queue, renames and
  synchronization committing onto a stray branch, and bulk renames leaving
  filesystem changes after a database rollback.
- **16 September.** Item 1: HTTP tests through the real application, which
  found sign-out never revoking refresh sessions. Item 7: every operational
  timestamp is UTC `timestamptz`. Backend module splits for invitations, users,
  Git operations, protocols and the Git and auth APIs. Item 8: self-maintenance,
  the installer, reported operations and audit export. Registration decomposed
  and translated. A refactoring pass removed about 2,000 lines of dead code,
  forwarding facades and copied logic, and found: a contact form that mailed `admin@example.com` when no administrator
  existed; email templates that never rendered and inserted unescaped user
  text; blank icons; dialogs styled from English words; and French and
  Japanese gaps across the interface. The
  password policy moved to NIST SP 800-63B with a breach check, and every API
  refusal gained a translatable code.
