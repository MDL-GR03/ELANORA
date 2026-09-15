"""Domain types for a lossless EAF projection.

The raw document is the source of truth. These immutable types are a typed
query projection covering every element type of the EAF 3.0 schema. Each keeps
its full attribute map as well, so an attribute without a dedicated field is
still preserved.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType

type StringMap = Mapping[str, str]


def immutable_attributes(values: dict[str, str]) -> StringMap:
    """Return a read-only copy of XML attributes."""
    return MappingProxyType(dict(values))


def parse_xsd_boolean(value: str | None) -> bool | None:
    """Read an xsd:boolean, which admits "1" and "0" as well as "true"/"false"."""
    if value is None:
        return None
    return value.strip() in {"true", "1"}


def split_references(value: str | None) -> tuple[str, ...]:
    """Split an xsd:IDREFS attribute into its individual references."""
    return tuple((value or "").split())


@dataclass(frozen=True, slots=True)
class EafLicense:
    """A LICENSE element: licence text and its URL."""

    url: str | None
    text: str
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class LinkedFileDescriptor:
    """A secondary file linked from the header, such as a transcript or sensor data."""

    link_url: str
    relative_link_url: str | None
    mime_type: str
    time_origin_ms: int | None
    associated_with: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafProperty:
    """A named document property from the header."""

    name: str | None
    value: str
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class LinguisticType:
    """A linguistic type: alignment, stereotype and vocabulary rules for tiers."""

    linguistic_type_id: str
    time_alignable: bool | None
    constraints: str | None
    graphic_references: bool | None
    controlled_vocabulary_ref: str | None
    ext_ref: str | None
    lexicon_ref: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafLocale:
    """An input locale."""

    language_code: str
    country_code: str | None
    variant: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafLanguage:
    """A content language referenced by tiers, annotations and vocabulary values."""

    lang_id: str
    lang_def: str | None
    lang_label: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafConstraint:
    """A tier stereotype constraint and its description."""

    stereotype: str
    description: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class MultilingualText:
    """Text in one referenced language."""

    lang_ref: str
    text: str


@dataclass(frozen=True, slots=True)
class ControlledVocabularyValue:
    """One language's value for a controlled vocabulary entry."""

    lang_ref: str
    value: str
    description: str | None


@dataclass(frozen=True, slots=True)
class ControlledVocabularyEntry:
    """An entry of a multilingual controlled vocabulary."""

    cve_id: str
    ext_ref: str | None
    values: tuple[ControlledVocabularyValue, ...]
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class ControlledVocabulary:
    """A controlled vocabulary with its descriptions and entries per language."""

    cv_id: str
    ext_ref: str | None
    descriptions: tuple[MultilingualText, ...]
    entries: tuple[ControlledVocabularyEntry, ...]
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class LexiconReference:
    """A reference to an external lexicon and data category."""

    lex_ref_id: str
    name: str
    type: str
    url: str
    lexicon_id: str
    lexicon_name: str
    datcat_id: str | None
    datcat_name: str | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class ExternalReference:
    """An external reference such as a data category or concept identifier."""

    ext_ref_id: str
    type: str
    value: str
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class CrossReferenceLink:
    """A link between two annotations or reference links."""

    ref_link_id: str
    name: str | None
    ref1: str
    ref2: str
    directionality: str | None
    ref_type: str | None
    lang_ref: str | None
    cve_ref: str | None
    ext_refs: tuple[str, ...]
    text: str
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class GroupReferenceLink:
    """A link grouping several annotations or reference links."""

    ref_link_id: str
    name: str | None
    refs: tuple[str, ...]
    ref_type: str | None
    lang_ref: str | None
    cve_ref: str | None
    ext_refs: tuple[str, ...]
    text: str
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class ReferenceLinkSet:
    """A named set of cross and group reference links."""

    link_set_id: str
    name: str | None
    ext_refs: tuple[str, ...]
    lang_ref: str | None
    cv_ref: str | None
    cross_links: tuple[CrossReferenceLink, ...]
    group_links: tuple[GroupReferenceLink, ...]
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class MediaDescriptor:
    """Media linked from an EAF header."""

    media_url: str
    mime_type: str
    relative_media_url: str | None
    extracted_from: str | None
    time_origin_ms: int | None
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafHeader:
    """EAF header and its complete set of child elements."""

    media_file: str
    time_units: str
    media_descriptors: tuple[MediaDescriptor, ...]
    linked_file_descriptors: tuple[LinkedFileDescriptor, ...]
    properties: tuple[EafProperty, ...]
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class AlignableAnnotation:
    """An annotation directly aligned to two time slots."""

    annotation_id: str
    value: str
    time_slot_ref1: str
    time_slot_ref2: str
    start_ms: int | None
    end_ms: int | None
    svg_ref: str | None
    cv_entry_ref: str | None
    ext_ref: str | None
    lang_ref: str | None
    attributes: StringMap

    @property
    def ext_refs(self) -> tuple[str, ...]:
        """Return each external reference cited by this annotation."""
        return split_references(self.ext_ref)

    @property
    def start_seconds(self) -> Decimal | None:
        """Return the aligned start in seconds when the slot is timed."""
        return Decimal(self.start_ms) / 1000 if self.start_ms is not None else None

    @property
    def end_seconds(self) -> Decimal | None:
        """Return the aligned end in seconds when the slot is timed."""
        return Decimal(self.end_ms) / 1000 if self.end_ms is not None else None


@dataclass(frozen=True, slots=True)
class ReferenceAnnotation:
    """An annotation whose alignment is inherited from another annotation."""

    annotation_id: str
    value: str
    annotation_ref: str
    previous_annotation: str | None
    cv_entry_ref: str | None
    ext_ref: str | None
    lang_ref: str | None
    attributes: StringMap

    @property
    def ext_refs(self) -> tuple[str, ...]:
        """Return each external reference cited by this annotation."""
        return split_references(self.ext_ref)


type EafAnnotation = AlignableAnnotation | ReferenceAnnotation


@dataclass(frozen=True, slots=True)
class EafTier:
    """A tier and all annotations in document order."""

    tier_id: str
    linguistic_type_ref: str
    parent_ref: str | None
    participant: str | None
    annotator: str | None
    default_locale: str | None
    lang_ref: str | None
    ext_ref: str | None
    annotations: tuple[EafAnnotation, ...]
    attributes: StringMap


@dataclass(frozen=True, slots=True)
class EafDocument:
    """Validated EAF document with a lossless original payload."""

    author: str
    date: str
    format_version: str
    version: str
    header: EafHeader
    time_slots: StringMap
    time_values_ms: MappingProxyType[str, int | None]
    tiers: tuple[EafTier, ...]
    linguistic_types: tuple[LinguisticType, ...]
    locales: tuple[EafLocale, ...]
    languages: tuple[EafLanguage, ...]
    constraints: tuple[EafConstraint, ...]
    controlled_vocabularies: tuple[ControlledVocabulary, ...]
    lexicon_references: tuple[LexiconReference, ...]
    external_references: tuple[ExternalReference, ...]
    licenses: tuple[EafLicense, ...]
    reference_link_sets: tuple[ReferenceLinkSet, ...]
    raw_xml: bytes = field(repr=False)
    sha256: str
    source_path: Path | None = None
    source_size: int = 0
    source_modified_at: datetime | None = None

    @property
    def annotations(self) -> tuple[EafAnnotation, ...]:
        """Return all annotations in tier and document order."""
        return tuple(
            annotation for tier in self.tiers for annotation in tier.annotations
        )
