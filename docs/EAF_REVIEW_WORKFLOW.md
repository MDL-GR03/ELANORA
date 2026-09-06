# EAF review workflow

## Product boundary

ELANORA is the collaboration, preservation, validation, and review layer around
ELAN. It does not replace ELAN as the annotation editor. Researchers correct
source files in ELAN and submit another immutable EAF revision.

Reviews must not expose Git commits, branches, XML lines, or merge markers as
the primary interaction. Those remain implementation and recovery details.
The review language is files, tiers, annotations, time intervals, protocol
findings, accepted revisions, and submitted revisions.

## Implemented first slice

The pending-contribution view can request a read-only semantic comparison of an
accepted EAF and a submitted EAF. The backend validates and parses both Git
blobs without changing the repository checkout. It compares annotations by
their stable EAF annotation identifier and reports:

- additions and removals;
- value changes;
- timing changes;
- tier moves;
- reference changes;
- the inherited media interval for reference annotations;
- linked-media references.

The browser presents accepted and submitted annotation values side by side.
It deliberately provides no XML textarea or partial file mutation. Whole-file
acceptance remains available through the existing contribution workflow. Mixed
or corrected results require a new upload from ELAN.

## Implemented second slice: durable review cases

The unused legacy comment and conflict tables have been replaced with
revision-scoped review cases. A case targets an immutable submission and may
optionally target one EAF file, tier, annotation, validation issue, and media
interval. It records an assignee, state, append-only discussion, author,
timestamps, and resolution evidence.

The implemented states are `open`, `changes_requested`, `resubmitted`,
`resolved`, and `closed`. Assignment and state transitions are audited. Project
readers may view cases; contributors may open and discuss them; project
administrators may assign, request changes, resolve, and close them. A
`resubmitted` transition must point at a new submission in the same project.
Backend authorization is authoritative.

The administrator contribution-resolution view supports opening a case
directly from an individual semantic annotation difference. The unified
Contributions workspace provides an Incoming work queue and a Questions and
corrections inbox. Readers can inspect the work, contributors can discuss it,
and administrators have assignment, decision, and acceptance controls.
Assignments and discussion
replies create in-app notifications linked back to the case. After a corrected
upload, the success screen links to the review inbox and lets its contributor
associate that immutable pending upload with the relevant requested-change
case.

## Acceptance policy

Every submission is based on the project's accepted Git revision and is stored
on an isolated branch. Merge readiness is calculated with Git's non-mutating
merge-tree operation, so merely viewing the queue never changes the checkout.
Immediately before acceptance, every EAF in the submitted revision is parsed
and validated again. When the project has pinned a published protocol, upload
checks each file against that exact immutable protocol version and records its
identifier and rule checksum with the contribution. Protocol errors reject the
whole batch before it enters project history; the original rejected bytes and
structured findings are retained for diagnosis. Acceptance then repeats the
check against the currently pinned protocol, so a protocol change made during
review cannot be bypassed. Open review cases block acceptance.

Administrators may enable automatic acceptance only for submissions containing
valid new files and no modifications, deletions, failed files, or unresolved
reviews. All other work remains in the review queue. A completed acceptance
records the submitter, base commit, accepted commit, acting user, strategy, and
an audit event; the contributor receives an in-app notification. Acceptance is
retry-safe when Git completed but the database projection needs rebuilding.

Repositories created by current ELANORA versions use `main`. The workflow also
detects and supports retained legacy repositories whose accepted branch is
named `master`.

## Retroactive corpus compliance

A published protocol can be evaluated against the latest accepted revision of
every EAF before it is activated. This impact scan is read-only: it does not
rewrite XML, rename files, or change the project's pinned protocol.

Each scan persists its protocol version, the exact revision selected for each
file, immutable validation runs and findings, initiator, trigger, timestamps,
and completion totals. Identical validation inputs reuse their evidence while
each scan remains a separate historical snapshot of the corpus.

Any finding can become a correction case linked to that exact validation
issue, even when it was discovered after the original contribution was
accepted. Discussion and assignment continue in Contributions. Researchers
make the correction in ELAN and submit a new revision; ELANORA never silently
changes accepted research data.

## Media preview slice

Media playback requires an institution-controlled asset rather than trusting a
path embedded in an EAF. Introduce the planned `AssetStore`, associate an
immutable media checksum with an EAF descriptor, and serve authorized range
requests. The review UI can then seek to and loop the semantic change interval.
Waveform and derived browser-compatible proxies are disposable derivatives;
the original media asset remains immutable.

## Safety invariants

- Uploaded EAF bytes are never rewritten by the preview.
- Comparing revisions never mutates Git or the working tree.
- Every accepted file is schema- and semantically valid.
- A new upload never silently closes review cases; it links a new revision and
  reruns validation before a reviewer resolves them.
- Media is never served from an unrestricted static directory.
