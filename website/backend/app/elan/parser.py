"""Typed EAF parser built on the validation boundary."""

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from types import MappingProxyType
from typing import cast

from lxml import etree

from app.elan.domain import (
    AlignableAnnotation,
    ControlledVocabulary,
    ControlledVocabularyEntry,
    ControlledVocabularyValue,
    CrossReferenceLink,
    EafAnnotation,
    EafConstraint,
    EafDocument,
    EafHeader,
    EafLanguage,
    EafLicense,
    EafLocale,
    EafProperty,
    EafTier,
    ExternalReference,
    GroupReferenceLink,
    LexiconReference,
    LinguisticType,
    LinkedFileDescriptor,
    MediaDescriptor,
    MultilingualText,
    ReferenceAnnotation,
    ReferenceLinkSet,
    StringMap,
    immutable_attributes,
)
from app.elan.validation import validate_eaf
from app.elan.xsd_types import parse_xsd_boolean, split_references


def _required(element: etree._Element, attribute: str) -> str:
    value = element.get(attribute)
    if value is None:
        raise AssertionError(f"validated element is missing {attribute}")
    return cast("str", value)


def _parse_optional_int(value: str | None) -> int | None:
    return int(value) if value is not None else None


def _attributes(element: etree._Element) -> StringMap:
    return immutable_attributes(
        {str(key): str(value) for key, value in element.attrib.items()}
    )


def _parse_linguistic_type(element: etree._Element) -> LinguisticType:
    return LinguisticType(
        linguistic_type_id=_required(element, "LINGUISTIC_TYPE_ID"),
        time_alignable=parse_xsd_boolean(element.get("TIME_ALIGNABLE")),
        constraints=element.get("CONSTRAINTS"),
        graphic_references=parse_xsd_boolean(element.get("GRAPHIC_REFERENCES")),
        controlled_vocabulary_ref=element.get("CONTROLLED_VOCABULARY_REF"),
        ext_ref=element.get("EXT_REF"),
        lexicon_ref=element.get("LEXICON_REF"),
        attributes=_attributes(element),
    )


def _parse_controlled_vocabulary(element: etree._Element) -> ControlledVocabulary:
    return ControlledVocabulary(
        cv_id=_required(element, "CV_ID"),
        ext_ref=element.get("EXT_REF"),
        descriptions=tuple(
            MultilingualText(lang_ref=_required(item, "LANG_REF"), text=item.text or "")
            for item in element.findall("DESCRIPTION")
        ),
        entries=tuple(
            ControlledVocabularyEntry(
                cve_id=_required(entry, "CVE_ID"),
                ext_ref=entry.get("EXT_REF"),
                values=tuple(
                    ControlledVocabularyValue(
                        lang_ref=_required(value, "LANG_REF"),
                        value=value.text or "",
                        description=value.get("DESCRIPTION"),
                    )
                    for value in entry.findall("CVE_VALUE")
                ),
                attributes=_attributes(entry),
            )
            for entry in element.findall("CV_ENTRY_ML")
        ),
        attributes=_attributes(element),
    )


def _parse_reference_link_set(element: etree._Element) -> ReferenceLinkSet:
    return ReferenceLinkSet(
        link_set_id=_required(element, "LINK_SET_ID"),
        name=element.get("LINK_SET_NAME"),
        ext_refs=split_references(element.get("EXT_REF")),
        lang_ref=element.get("LANG_REF"),
        cv_ref=element.get("CV_REF"),
        cross_links=tuple(
            CrossReferenceLink(
                ref_link_id=_required(link, "REF_LINK_ID"),
                name=link.get("REF_LINK_NAME"),
                ref1=_required(link, "REF1"),
                ref2=_required(link, "REF2"),
                directionality=link.get("DIRECTIONALITY"),
                ref_type=link.get("REF_TYPE"),
                lang_ref=link.get("LANG_REF"),
                cve_ref=link.get("CVE_REF"),
                ext_refs=split_references(link.get("EXT_REF")),
                text=link.text or "",
                attributes=_attributes(link),
            )
            for link in element.findall("CROSS_REF_LINK")
        ),
        group_links=tuple(
            GroupReferenceLink(
                ref_link_id=_required(link, "REF_LINK_ID"),
                name=link.get("REF_LINK_NAME"),
                refs=split_references(_required(link, "REFS")),
                ref_type=link.get("REF_TYPE"),
                lang_ref=link.get("LANG_REF"),
                cve_ref=link.get("CVE_REF"),
                ext_refs=split_references(link.get("EXT_REF")),
                text=link.text or "",
                attributes=_attributes(link),
            )
            for link in element.findall("GROUP_REF_LINK")
        ),
        attributes=_attributes(element),
    )


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
            lang_ref=element.get("LANG_REF"),
            attributes=attributes,
        )
    return ReferenceAnnotation(
        annotation_id=_required(element, "ANNOTATION_ID"),
        value=_annotation_value(element),
        annotation_ref=_required(element, "ANNOTATION_REF"),
        previous_annotation=element.get("PREVIOUS_ANNOTATION"),
        cv_entry_ref=element.get("CVE_REF"),
        ext_ref=element.get("EXT_REF"),
        lang_ref=element.get("LANG_REF"),
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
            LinkedFileDescriptor(
                link_url=_required(item, "LINK_URL"),
                relative_link_url=item.get("RELATIVE_LINK_URL"),
                mime_type=_required(item, "MIME_TYPE"),
                time_origin_ms=_parse_optional_int(item.get("TIME_ORIGIN")),
                associated_with=item.get("ASSOCIATED_WITH"),
                attributes=_attributes(item),
            )
            for item in header_element.findall("LINKED_FILE_DESCRIPTOR")
        ),
        properties=tuple(
            EafProperty(
                name=item.get("NAME"),
                value=item.text or "",
                attributes=_attributes(item),
            )
            for item in header_element.findall("PROPERTY")
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
            _parse_linguistic_type(item) for item in root.findall("LINGUISTIC_TYPE")
        ),
        locales=tuple(
            EafLocale(
                language_code=_required(item, "LANGUAGE_CODE"),
                country_code=item.get("COUNTRY_CODE"),
                variant=item.get("VARIANT"),
                attributes=_attributes(item),
            )
            for item in root.findall("LOCALE")
        ),
        languages=tuple(
            EafLanguage(
                lang_id=_required(item, "LANG_ID"),
                lang_def=item.get("LANG_DEF"),
                lang_label=item.get("LANG_LABEL"),
                attributes=_attributes(item),
            )
            for item in root.findall("LANGUAGE")
        ),
        constraints=tuple(
            EafConstraint(
                stereotype=_required(item, "STEREOTYPE"),
                description=item.get("DESCRIPTION"),
                attributes=_attributes(item),
            )
            for item in root.findall("CONSTRAINT")
        ),
        controlled_vocabularies=tuple(
            _parse_controlled_vocabulary(item)
            for item in root.findall("CONTROLLED_VOCABULARY")
        ),
        lexicon_references=tuple(
            LexiconReference(
                lex_ref_id=_required(item, "LEX_REF_ID"),
                name=_required(item, "NAME"),
                type=_required(item, "TYPE"),
                url=_required(item, "URL"),
                lexicon_id=_required(item, "LEXICON_ID"),
                lexicon_name=_required(item, "LEXICON_NAME"),
                datcat_id=item.get("DATCAT_ID"),
                datcat_name=item.get("DATCAT_NAME"),
                attributes=_attributes(item),
            )
            for item in root.findall("LEXICON_REF")
        ),
        external_references=tuple(
            ExternalReference(
                ext_ref_id=_required(item, "EXT_REF_ID"),
                type=_required(item, "TYPE"),
                value=_required(item, "VALUE"),
                attributes=_attributes(item),
            )
            for item in root.findall("EXTERNAL_REF")
        ),
        licenses=tuple(
            EafLicense(
                url=item.get("LICENSE_URL"),
                text=item.text or "",
                attributes=_attributes(item),
            )
            for item in root.findall("LICENSE")
        ),
        reference_link_sets=tuple(
            _parse_reference_link_set(item) for item in root.findall("REF_LINK_SET")
        ),
        raw_xml=content,
        sha256=hashlib.sha256(content).hexdigest(),
        source_path=path,
        source_size=len(content),
        source_modified_at=datetime.fromtimestamp(stat.st_mtime, UTC)
        if stat is not None
        else None,
    )


def parse_eaf_path(path: Path) -> EafDocument:
    """Read, validate, and parse an EAF file from disk."""
    return parse_eaf(path.read_bytes(), source_path=path)
