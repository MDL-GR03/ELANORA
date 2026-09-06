# EAF ingestion policy

ELANORA treats submitted bytes, interpreted annotation data, and accepted
project history as separate records. A successful XML parse alone is not an
acceptance decision.

## Validation boundary

Every regular upload and folder-based project import applies the same checks:

1. Enforce filename and configured byte limits.
2. Parse XML with external entities, DTD loading, recovery, and network access
   disabled.
3. Validate against the vendored official EAF 3.0 schema.
4. Validate identifiers, references, tier relationships, annotation timing,
   controlled vocabularies, and other ELANORA semantic invariants.

A valid submission can enter the pending-review branch workflow. Research work
may be incomplete while remaining structurally valid; project-specific
completion rules belong to review and protocol validation rather than XML
recovery.

## Rejected submissions

If a safely bounded `.eaf` payload fails structural or semantic validation, the
whole batch is rejected with HTTP 422. ELANORA stores an immutable
`EAF_INGESTION_ATTEMPT` containing:

- the exact submitted bytes and SHA-256 digest;
- institution, project target, filename, and submitter identifiers;
- every structured validation issue and its document location;
- submission time and rejected status.

Rejected attempts never become `EAF_REVISION` rows and never enter a Git
branch. The API returns at most 20 issue details per file while retaining the
complete issue list in the database. Size, filename, and dangerous media-type
failures are rejected before preservation because they do not satisfy the safe
EAF ingestion envelope.

## Repairs

Ingestion never modifies a source document. A repair must create a derivative
with its own digest and a recorded mapping from the original. Deterministic
suggestions may be offered when exactly one replacement satisfies the schema,
semantic rules, and project protocol. A researcher or authorized reviewer must
approve the derivative before it is submitted again and accepted as an
immutable EAF revision. Ambiguous changes always require domain judgment.

Deployments must apply Alembic migration `0002` before accepting uploads with
this policy. Access to rejected payloads should remain institution-scoped, and
retention periods should be set according to the institution's research-data
and privacy policy.
