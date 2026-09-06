# EAF repair record

## `Annotation_S059.eaf` — 2026-09-04

The source was repaired without changing annotation text, tier structure, or
time values.

- Original SHA-256: `0b84578ecabba67c828b7c590c8eff937faa524a66055c1bdbc1ca9b3941d982`
- Repaired SHA-256: `77e9e7eecec072ba7271379f2069e9dc51755453defb1dd4ffbacac4cbc57648`
- `ts8999` was restored to `ts1`. Repository history shows that commit
  `3d4e9bb` changed the previously valid `ts1` identifier without updating its
  annotation reference.
- 488 `CVE_REF` attributes, representing 10 distinct obsolete identifiers,
  were replaced with the unique current entry having the same annotation value
  in the controlled vocabulary selected by the tier's linguistic type.
- Every mapping was unique; no annotation value required interpretation or
  manual selection.
- The repaired EAF passes the vendored EAF 3.0 XSD and all ELANORA semantic
  checks, and it opens in ELAN 7.1.

The original bytes remain recoverable from Git history. Future repairs must be
performed on a derivative, documented here, and accepted only after complete
validation; ingestion must never silently modify a submitted source document.
