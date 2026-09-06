"""Typed EAF parser built on the validation boundary."""

import hashlib
from datetime import datetime
from pathlib import Path
from types import MappingProxyType
from typing import cast

from lxml import etree

from app.elan.domain import (
    AlignableAnnotation,
    EafAnnotation,
    EafDocument,
    EafHeader,
    EafTier,
    ElementSnapshot,
    MediaDescriptor,
    ReferenceAnnotation,
    immutable_attributes,
)
from app.elan.validation import validate_eaf


def _snapshot(element: etree._Element) -> ElementSnapshot:
    return ElementSnapshot(
        tag=str(element.tag),
        attributes=immutable_attributes(
            {str(key): value for key, value in element.attrib.items()}
        ),
        text=element.text,
        xml=etree.tostring(element, encoding="utf-8", with_tail=False),
    )


def _required(element: etree._Element, attribute: str) -> str:
    value = element.get(attribute)
    if value is None:
        raise AssertionError(f"validated element is missing {attribute}")
    return cast("str", value)


def _parse_optional_int(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _annotation_value(element: etree._Element) -> str:
    value = element.find("ANNOTATION_VALUE")
    if value is None:
        raise AssertionError("validated annotation has no value element")
    return value.text or ""


def _parse_annotation(
    element: etree._Element, time_values: dict[str, int | None]
) -> EafAnnotation:
    attributes = immutable_attributes(
        {str(key): value for key, value in element.attrib.items()}
    )
    if element.tag == "ALIGNABLE_ANNOTATION":
        start_ref = _required(element, "TIME_SLOT_REF1")
        end_ref = _required(element, "TIME_SLOT_REF2")
        return AlignableAnnotation(
            annotation_id=_required(element, "ANNOTATION_ID"),
            value=_annotation_value(element),
            time_slot_ref1=start_ref,
            time_slot_ref2=end_ref,
            start_ms=time_values[start_ref],
            end_ms=time_values[end_ref],
            svg_ref=element.get("SVG_REF"),
            cv_entry_ref=element.get("CVE_REF"),
            ext_ref=element.get("EXT_REF"),
            attributes=attributes,
        )
    return ReferenceAnnotation(
        annotation_id=_required(element, "ANNOTATION_ID"),
        value=_annotation_value(element),
        annotation_ref=_required(element, "ANNOTATION_REF"),
        previous_annotation=element.get("PREVIOUS_ANNOTATION"),
        cv_entry_ref=element.get("CVE_REF"),
        ext_ref=element.get("EXT_REF"),
        attributes=attributes,
    )


def parse_eaf(content: bytes, *, source_path: Path | None = None) -> EafDocument:
    """Validate and parse EAF bytes without discarding source information."""
    root = validate_eaf(content)
    header_element = root.find("HEADER")
    time_order = root.find("TIME_ORDER")
    if header_element is None or time_order is None:
        raise AssertionError("validated EAF is missing required elements")

    time_values = {
        _required(slot, "TIME_SLOT_ID"): _parse_optional_int(slot.get("TIME_VALUE"))
        for slot in time_order.findall("TIME_SLOT")
    }
    time_slot_attributes = {
        slot_id: "" if value is None else str(value)
        for slot_id, value in time_values.items()
    }

    media_descriptors = tuple(
        MediaDescriptor(
            media_url=_required(item, "MEDIA_URL"),
            mime_type=_required(item, "MIME_TYPE"),
            relative_media_url=item.get("RELATIVE_MEDIA_URL"),
            extracted_from=item.get("EXTRACTED_FROM"),
            time_origin_ms=_parse_optional_int(item.get("TIME_ORIGIN")),
            attributes=immutable_attributes(
                {str(key): value for key, value in item.attrib.items()}
            ),
        )
        for item in header_element.findall("MEDIA_DESCRIPTOR")
    )
    header = EafHeader(
        media_file=header_element.get("MEDIA_FILE", ""),
        time_units=_required(header_element, "TIME_UNITS"),
        media_descriptors=media_descriptors,
        linked_file_descriptors=tuple(
            _snapshot(item) for item in header_element.findall("LINKED_FILE_DESCRIPTOR")
        ),
        properties=tuple(
            _snapshot(item) for item in header_element.findall("PROPERTY")
        ),
        attributes=immutable_attributes(
            {str(key): value for key, value in header_element.attrib.items()}
        ),
    )

    tiers: list[EafTier] = []
    for tier in root.findall("TIER"):
        annotations = tuple(
            _parse_annotation(item, time_values)
            for item in tier.findall("./ANNOTATION/*")
        )
        tiers.append(
            EafTier(
                tier_id=_required(tier, "TIER_ID"),
                linguistic_type_ref=_required(tier, "LINGUISTIC_TYPE_REF"),
                parent_ref=tier.get("PARENT_REF"),
                participant=tier.get("PARTICIPANT"),
                annotator=tier.get("ANNOTATOR"),
                default_locale=tier.get("DEFAULT_LOCALE"),
                lang_ref=tier.get("LANG_REF"),
                ext_ref=tier.get("EXT_REF"),
                annotations=annotations,
                attributes=immutable_attributes(
                    {str(key): value for key, value in tier.attrib.items()}
                ),
            )
        )

    path = source_path.resolve() if source_path is not None else None
    stat = path.stat() if path is not None else None
    return EafDocument(
        author=_required(root, "AUTHOR"),
        date=_required(root, "DATE"),
        format_version=_required(root, "FORMAT"),
        version=_required(root, "VERSION"),
        header=header,
        time_slots=MappingProxyType(time_slot_attributes),
        time_values_ms=MappingProxyType(time_values),
        tiers=tuple(tiers),
        linguistic_types=tuple(
            _snapshot(item) for item in root.findall("LINGUISTIC_TYPE")
        ),
        locales=tuple(_snapshot(item) for item in root.findall("LOCALE")),
        languages=tuple(_snapshot(item) for item in root.findall("LANGUAGE")),
        constraints=tuple(_snapshot(item) for item in root.findall("CONSTRAINT")),
        controlled_vocabularies=tuple(
            _snapshot(item) for item in root.findall("CONTROLLED_VOCABULARY")
        ),
        external_references=tuple(
            _snapshot(item) for item in root.findall("EXTERNAL_REF")
        ),
        licenses=tuple(_snapshot(item) for item in root.findall("LICENSE")),
        reference_link_sets=tuple(
            _snapshot(item) for item in root.findall("REF_LINK_SET")
        ),
        raw_xml=content,
        sha256=hashlib.sha256(content).hexdigest(),
        source_path=path,
        source_size=len(content),
        source_modified_at=datetime.fromtimestamp(stat.st_mtime)
        if stat is not None
        else None,
    )


def parse_eaf_path(path: Path) -> EafDocument:
    """Read, validate, and parse an EAF file from disk."""
    return parse_eaf(path.read_bytes(), source_path=path)
