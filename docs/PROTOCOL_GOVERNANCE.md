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

The project configuration page now includes a **Versioned Protocol** editor for
creating, publishing, and pinning these snapshots. The same API is exposed
below `/api/v1/projects/{project_id}` and documented at `/docs` in development.

## Validation evidence

A validation is identified by the immutable tuple of EAF revision, published
protocol version, and validator release. Repeating identical inputs returns the
same run. Each run records a `passed` or `failed` outcome and ordered issues
with a stable code, severity, XML location, message, and optional protocol rule
key.

The validator release checksum covers the vendored EAF XSD and deterministic
protocol-validation implementation. Changing either without incrementing the
release version stops validation rather than silently changing historical
meaning. PostgreSQL triggers prevent updates or deletion of validator releases,
validation runs, validation issues, and published protocol versions.

The exact EAF revision bytes remain authoritative and are never rewritten by
validation.
