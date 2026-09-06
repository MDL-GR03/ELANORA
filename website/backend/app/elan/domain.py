"""Domain types for a lossless EAF projection.

The raw document is the source of truth.  These immutable types are a query
projection and deliberately retain attributes and serialized elements that the
application does not yet interpret.
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


@dataclass(frozen=True, slots=True)
class ElementSnapshot:
    """Lossless snapshot of an XML element not represented more specifically."""

    tag: str
    attributes: StringMap
    text: str | None
    xml: bytes


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
    linked_file_descriptors: tuple[ElementSnapshot, ...]
    properties: tuple[ElementSnapshot, ...]
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
    attributes: StringMap

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
    attributes: StringMap


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
    linguistic_types: tuple[ElementSnapshot, ...]
    locales: tuple[ElementSnapshot, ...]
    languages: tuple[ElementSnapshot, ...]
    constraints: tuple[ElementSnapshot, ...]
    controlled_vocabularies: tuple[ElementSnapshot, ...]
    external_references: tuple[ElementSnapshot, ...]
    licenses: tuple[ElementSnapshot, ...]
    reference_link_sets: tuple[ElementSnapshot, ...]
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
