"""Versioned JSON projection of a validated EAF document."""

from typing import Any

from app.elan.domain import (
    AlignableAnnotation,
    EafDocument,
    ElementSnapshot,
    ReferenceAnnotation,
)

EAF_PROJECTION_VERSION = "1"


def _element(element: ElementSnapshot) -> dict[str, Any]:
    return {
        "tag": element.tag,
        "attributes": dict(element.attributes),
        "text": element.text,
        "xml": element.xml.decode("utf-8"),
    }


def document_projection(document: EafDocument) -> dict[str, Any]:
    """Return a complete JSON-compatible query projection of an EAF document."""
    tiers: list[dict[str, Any]] = []
    for tier in document.tiers:
        annotations: list[dict[str, Any]] = []
        for annotation in tier.annotations:
            common: dict[str, Any] = {
                "annotation_id": annotation.annotation_id,
                "value": annotation.value,
                "cv_entry_ref": annotation.cv_entry_ref,
                "external_ref": annotation.ext_ref,
                "attributes": dict(annotation.attributes),
            }
            if isinstance(annotation, AlignableAnnotation):
                common.update(
                    {
                        "kind": "alignable",
                        "time_slot_ref1": annotation.time_slot_ref1,
                        "time_slot_ref2": annotation.time_slot_ref2,
                        "start_ms": annotation.start_ms,
                        "end_ms": annotation.end_ms,
                        "svg_ref": annotation.svg_ref,
                    }
                )
            elif isinstance(annotation, ReferenceAnnotation):
                common.update(
                    {
                        "kind": "reference",
                        "annotation_ref": annotation.annotation_ref,
                        "previous_annotation": annotation.previous_annotation,
                    }
                )
            annotations.append(common)
        tiers.append(
            {
                "tier_id": tier.tier_id,
                "linguistic_type_ref": tier.linguistic_type_ref,
                "parent_ref": tier.parent_ref,
                "participant": tier.participant,
                "annotator": tier.annotator,
                "default_locale": tier.default_locale,
                "language_ref": tier.lang_ref,
                "external_ref": tier.ext_ref,
                "attributes": dict(tier.attributes),
                "annotations": annotations,
            }
        )

    return {
        "projection_version": EAF_PROJECTION_VERSION,
        "document": {
            "author": document.author,
            "date": document.date,
            "format": document.format_version,
            "version": document.version,
        },
        "header": {
            "media_file": document.header.media_file,
            "time_units": document.header.time_units,
            "attributes": dict(document.header.attributes),
            "media_descriptors": [
                {
                    "media_url": item.media_url,
                    "mime_type": item.mime_type,
                    "relative_media_url": item.relative_media_url,
                    "extracted_from": item.extracted_from,
                    "time_origin_ms": item.time_origin_ms,
                    "attributes": dict(item.attributes),
                }
                for item in document.header.media_descriptors
            ],
            "linked_file_descriptors": [
                _element(item) for item in document.header.linked_file_descriptors
            ],
            "properties": [_element(item) for item in document.header.properties],
        },
        "time_slots": dict(document.time_values_ms),
        "tiers": tiers,
        "linguistic_types": [_element(item) for item in document.linguistic_types],
        "locales": [_element(item) for item in document.locales],
        "languages": [_element(item) for item in document.languages],
        "constraints": [_element(item) for item in document.constraints],
        "controlled_vocabularies": [
            _element(item) for item in document.controlled_vocabularies
        ],
        "external_references": [
            _element(item) for item in document.external_references
        ],
        "licenses": [_element(item) for item in document.licenses],
        "reference_link_sets": [
            _element(item) for item in document.reference_link_sets
        ],
    }
