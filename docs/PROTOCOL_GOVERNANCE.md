# Protocol governance

ELANORA protocols belong to the institution installation. A protocol has a
stable identity and numbered versions. Draft versions may be replaced; a
published version is immutable in both the service layer and PostgreSQL.

Projects explicitly pin one published version. Existing projects remain
unversioned after migration and continue using the legacy mutable standards
until an administrator deliberately creates, publishes and pins a protocol.
This avoids silently assigning new rules to existing research.

## Permission model

`manage_protocols` is a project capability, not a project access level.
Institution administrators and project owners have it implicitly. A project
administrator can delegate it to an existing member from **Members and
Access** without granting that person general project administration. Removing
the member also removes the capability through a composite database foreign
key.

The capability authorizes creating and editing drafts, publishing versions,
pinning a project version, and initiating persisted validation. Project
administrators manage capability grants. All project members with read access
may list the institution's available protocol versions.

## Supported immutable rules

The typed rule snapshot currently supports required tier IDs, required parent
relationships, required tier-to-linguistic-type assignments, required
controlled-vocabulary IDs, mandatory linked media, and an allow-list of media
MIME types. Empty identifiers, relationship rules for non-required tiers, and
unknown fields are rejected. New rule families must receive typed validation
and deterministic tests rather than being stored as uninterpreted settings.

Example request body:

```json
{
  "name": "LSFB baseline",
  "description": "Required corpus tiers",
  "rules": {
    "required_tiers": ["utterance", "translation"],
    "tier_parents": {"translation": "utterance"},
    "tier_linguistic_types": {
      "utterance": "utterance-type",
      "translation": "translation-type"
    },
    "required_controlled_vocabularies": ["greetings"],
    "media_required": true,
    "allowed_media_mime_types": ["video/mp4"]
  }
}
```

### Rule severity

Every rule is an `error` unless the snapshot's `severities` map says otherwise,
so versions published before severities existed keep their meaning. For
example, `"severities": {"required_tiers": "warning"}` turns a missing required
tier into a warning. Keys must name a rule the snapshot supports.

- An **error** refuses the upload, fails the validation run and prevents a
  contribution from being accepted.
- A **warning** lets the upload through and the run pass. Warnings are kept as
  validation issues with severity `warning`, stored with the contribution (at
  most 200 per upload) and shown to reviewers in the pending queue.

All three decisions use one definition, `blocking_findings` in
`app/service/protocol_evaluation.py`.

The project configuration page now includes a **Versioned Protocol** editor for
creating, publishing, and pinning these snapshots. The same API is exposed
below `/api/v1/projects/{project_id}` and documented at `/docs` in development.

## Validation evidence

A validation is identified by the immutable tuple of EAF revision, published
protocol version, and validator release. Repeating identical inputs returns the
same run. Each run records a `passed` or `failed` outcome and ordered issues
with a stable code, severity, XML location, message, and optional protocol rule
key.

The validator release checksum covers exactly the sources that decide an
outcome, listed in `VALIDATOR_SOURCES` in `app/service/protocol_evaluation.py`:
the vendored EAF XSD, the semantic EAF validator, the XML Schema datatype
readers, and the protocol rule evaluator. Changing any of them without
incrementing `VALIDATOR_VERSION` stops validation rather than silently changing
historical meaning. Protocol administration, compliance scans and corpus
suggestions live elsewhere and can change without a new release.

Release 1 fingerprinted the whole protocol service instead. Any unrelated edit
to it would have halted validation, while the semantic validator, which does
change outcomes, was not covered. Release 2 corrects the scope and records two
semantic fixes: annotations citing several external references, and
`xsd:boolean` values written as `1` or `0`, both of which release 1 wrongly
rejected. Runs recorded under release 1 keep their original release. PostgreSQL triggers prevent updates or deletion of validator releases,
validation runs, validation issues, and published protocol versions.

The exact EAF revision bytes remain authoritative and are never rewritten by
validation.
