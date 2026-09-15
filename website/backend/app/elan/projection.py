"""Versioned JSON projection of a validated EAF document.

The projection is derived from source bytes stored alongside it, so it can
always be rebuilt. Version 2 gives every EAF 3.0 element type a typed, queryable
shape; version 1 kept most of them as serialized XML snippets and omitted
lexicon references altogether.

Every projected element carries its schema attributes as typed fields. Its
``attributes`` map holds only the attributes without a dedicated field, so the
typed fields and that map together account for every attribute in the source.
"""

from typing import Any

from app.elan.domain import (
    AlignableAnnotation,
    ControlledVocabulary,
    EafAnnotation,
    EafDocument,
    ReferenceLinkSet,
    StringMap,
    split_references,
)

EAF_PROJECTION_VERSION = "2"

_ANNOTATION_COMMON = {"ANNOTATION_ID", "CVE_REF", "EXT_REF", "LANG_REF"}
_TYPED_ATTRIBUTES: dict[str, frozenset[str]] = {
    "header": frozenset({"MEDIA_FILE", "TIME_UNITS"}),
    "license": frozenset({"LICENSE_URL"}),
    "media": frozenset(
        {
            "MEDIA_URL",
            "MIME_TYPE",
            "RELATIVE_MEDIA_URL",
            "EXTRACTED_FROM",
            "TIME_ORIGIN",
        }
    ),
    "linked_file": frozenset(
        {"LINK_URL", "RELATIVE_LINK_URL", "MIME_TYPE", "TIME_ORIGIN", "ASSOCIATED_WITH"}
    ),
    "property": frozenset({"NAME"}),
    "tier": frozenset(
        {
            "TIER_ID",
            "LINGUISTIC_TYPE_REF",
            "PARENT_REF",
            "PARTICIPANT",
            "ANNOTATOR",
            "DEFAULT_LOCALE",
            "LANG_REF",
            "EXT_REF",
        }
    ),
    "alignable": frozenset(
        _ANNOTATION_COMMON | {"TIME_SLOT_REF1", "TIME_SLOT_REF2", "SVG_REF"}
    ),
    "reference": frozenset(
        _ANNOTATION_COMMON | {"ANNOTATION_REF", "PREVIOUS_ANNOTATION"}
    ),
    "linguistic_type": frozenset(
        {
            "LINGUISTIC_TYPE_ID",
            "TIME_ALIGNABLE",
            "CONSTRAINTS",
            "GRAPHIC_REFERENCES",
            "CONTROLLED_VOCABULARY_REF",
            "EXT_REF",
            "LEXICON_REF",
        }
    ),
    "locale": frozenset({"LANGUAGE_CODE", "COUNTRY_CODE", "VARIANT"}),
    "language": frozenset({"LANG_ID", "LANG_DEF", "LANG_LABEL"}),
    "constraint": frozenset({"STEREOTYPE", "DESCRIPTION"}),
    "vocabulary": frozenset({"CV_ID", "EXT_REF"}),
    "vocabulary_entry": frozenset({"CVE_ID", "EXT_REF"}),
    "lexicon": frozenset(
        {
            "LEX_REF_ID",
            "NAME",
            "TYPE",
            "URL",
            "LEXICON_ID",
            "LEXICON_NAME",
            "DATCAT_ID",
            "DATCAT_NAME",
        }
    ),
    "external_reference": frozenset({"EXT_REF_ID", "TYPE", "VALUE"}),
    "link_set": frozenset(
        {"LINK_SET_ID", "LINK_SET_NAME", "EXT_REF", "LANG_REF", "CV_REF"}
    ),
    "cross_link": frozenset(
        {
            "REF_LINK_ID",
            "REF_LINK_NAME",
            "REF1",
            "REF2",
            "DIRECTIONALITY",
            "REF_TYPE",
            "LANG_REF",
            "CVE_REF",
            "EXT_REF",
        }
    ),
    "group_link": frozenset(
        {
            "REF_LINK_ID",
            "REF_LINK_NAME",
            "REFS",
            "REF_TYPE",
            "LANG_REF",
            "CVE_REF",
            "EXT_REF",
        }
    ),
}


def _extra(values: StringMap, kind: str) -> dict[str, str]:
    """Attributes with no dedicated field in this element's projection."""
    typed = _TYPED_ATTRIBUTES[kind]
    return {key: value for key, value in values.items() if key not in typed}


def _annotation(annotation: EafAnnotation) -> dict[str, Any]:
    projected: dict[str, Any] = {
        "annotation_id": annotation.annotation_id,
        "value": annotation.value,
        "cv_entry_ref": annotation.cv_entry_ref,
        "external_refs": list(annotation.ext_refs),
        "language_ref": annotation.lang_ref,
    }
    if isinstance(annotation, AlignableAnnotation):
        projected.update(
            {
                "kind": "alignable",
                "time_slot_ref1": annotation.time_slot_ref1,
                "time_slot_ref2": annotation.time_slot_ref2,
                "start_ms": annotation.start_ms,
                "end_ms": annotation.end_ms,
                "svg_ref": annotation.svg_ref,
                "attributes": _extra(annotation.attributes, "alignable"),
            }
        )
    else:
        projected.update(
            {
                "kind": "reference",
                "annotation_ref": annotation.annotation_ref,
                "previous_annotation": annotation.previous_annotation,
                "attributes": _extra(annotation.attributes, "reference"),
            }
        )
    return projected


def _controlled_vocabulary(vocabulary: ControlledVocabulary) -> dict[str, Any]:
    return {
        "cv_id": vocabulary.cv_id,
        "external_refs": list(split_references(vocabulary.ext_ref)),
        "descriptions": [
            {"lang_ref": item.lang_ref, "text": item.text}
            for item in vocabulary.descriptions
        ],
        "entries": [
            {
                "cve_id": entry.cve_id,
                "external_refs": list(split_references(entry.ext_ref)),
                "values": [
                    {
                        "lang_ref": value.lang_ref,
                        "value": value.value,
                        "description": value.description,
                    }
                    for value in entry.values
                ],
                "attributes": _extra(entry.attributes, "vocabulary_entry"),
            }
            for entry in vocabulary.entries
        ],
        "attributes": _extra(vocabulary.attributes, "vocabulary"),
    }


def _reference_link_set(link_set: ReferenceLinkSet) -> dict[str, Any]:
    return {
        "link_set_id": link_set.link_set_id,
        "name": link_set.name,
        "external_refs": list(link_set.ext_refs),
        "lang_ref": link_set.lang_ref,
        "cv_ref": link_set.cv_ref,
        "cross_links": [
            {
                "ref_link_id": link.ref_link_id,
                "name": link.name,
                "ref1": link.ref1,
                "ref2": link.ref2,
                "directionality": link.directionality,
                "ref_type": link.ref_type,
                "lang_ref": link.lang_ref,
                "cve_ref": link.cve_ref,
                "external_refs": list(link.ext_refs),
                "text": link.text,
                "attributes": _extra(link.attributes, "cross_link"),
            }
            for link in link_set.cross_links
        ],
        "group_links": [
            {
                "ref_link_id": link.ref_link_id,
                "name": link.name,
                "refs": list(link.refs),
                "ref_type": link.ref_type,
                "lang_ref": link.lang_ref,
                "cve_ref": link.cve_ref,
                "external_refs": list(link.ext_refs),
                "text": link.text,
                "attributes": _extra(link.attributes, "group_link"),
            }
            for link in link_set.group_links
        ],
        "attributes": _extra(link_set.attributes, "link_set"),
    }


def document_projection(document: EafDocument) -> dict[str, Any]:
    """Return a complete, typed, JSON-compatible projection of an EAF document."""
    header = document.header
    return {
        "projection_version": EAF_PROJECTION_VERSION,
        "document": {
            "author": document.author,
            "date": document.date,
            "format": document.format_version,
            "version": document.version,
        },
        "licenses": [
            {
                "url": item.url,
                "text": item.text,
                "attributes": _extra(item.attributes, "license"),
            }
            for item in document.licenses
        ],
        "header": {
            "media_file": header.media_file,
            "time_units": header.time_units,
            "attributes": _extra(header.attributes, "header"),
            "media_descriptors": [
                {
                    "media_url": item.media_url,
                    "mime_type": item.mime_type,
                    "relative_media_url": item.relative_media_url,
                    "extracted_from": item.extracted_from,
                    "time_origin_ms": item.time_origin_ms,
                    "attributes": _extra(item.attributes, "media"),
                }
                for item in header.media_descriptors
            ],
            "linked_files": [
                {
                    "link_url": item.link_url,
                    "relative_link_url": item.relative_link_url,
                    "mime_type": item.mime_type,
                    "time_origin_ms": item.time_origin_ms,
                    "associated_with": item.associated_with,
                    "attributes": _extra(item.attributes, "linked_file"),
                }
                for item in header.linked_file_descriptors
            ],
            "properties": [
                {
                    "name": item.name,
                    "value": item.value,
                    "attributes": _extra(item.attributes, "property"),
                }
                for item in header.properties
            ],
        },
        "time_slots": dict(document.time_values_ms),
        "tiers": [
            {
                "tier_id": tier.tier_id,
                "linguistic_type_ref": tier.linguistic_type_ref,
                "parent_ref": tier.parent_ref,
                "participant": tier.participant,
                "annotator": tier.annotator,
                "default_locale": tier.default_locale,
                "language_ref": tier.lang_ref,
                "external_ref": tier.ext_ref,
                "attributes": _extra(tier.attributes, "tier"),
                "annotations": [_annotation(item) for item in tier.annotations],
            }
            for tier in document.tiers
        ],
        "linguistic_types": [
            {
                "linguistic_type_id": item.linguistic_type_id,
                "time_alignable": item.time_alignable,
                "constraints": item.constraints,
                "graphic_references": item.graphic_references,
                "controlled_vocabulary_ref": item.controlled_vocabulary_ref,
                "external_ref": item.ext_ref,
                "lexicon_ref": item.lexicon_ref,
                "attributes": _extra(item.attributes, "linguistic_type"),
            }
            for item in document.linguistic_types
        ],
        "locales": [
            {
                "language_code": item.language_code,
                "country_code": item.country_code,
                "variant": item.variant,
                "attributes": _extra(item.attributes, "locale"),
            }
            for item in document.locales
        ],
        "languages": [
            {
                "lang_id": item.lang_id,
                "lang_def": item.lang_def,
                "lang_label": item.lang_label,
                "attributes": _extra(item.attributes, "language"),
            }
            for item in document.languages
        ],
        "constraints": [
            {
                "stereotype": item.stereotype,
                "description": item.description,
                "attributes": _extra(item.attributes, "constraint"),
            }
            for item in document.constraints
        ],
        "controlled_vocabularies": [
            _controlled_vocabulary(item) for item in document.controlled_vocabularies
        ],
        "lexicon_references": [
            {
                "lex_ref_id": item.lex_ref_id,
                "name": item.name,
                "type": item.type,
                "url": item.url,
                "lexicon_id": item.lexicon_id,
                "lexicon_name": item.lexicon_name,
                "datcat_id": item.datcat_id,
                "datcat_name": item.datcat_name,
                "attributes": _extra(item.attributes, "lexicon"),
            }
            for item in document.lexicon_references
        ],
        "external_references": [
            {
                "ext_ref_id": item.ext_ref_id,
                "type": item.type,
                "value": item.value,
                "attributes": _extra(item.attributes, "external_reference"),
            }
            for item in document.external_references
        ],
        "reference_link_sets": [
            _reference_link_set(item) for item in document.reference_link_sets
        ],
    }
