"""Projection from parsed EAF documents into the relational persistence shape.

New EAF code should consume :class:`app.elan.domain.EafDocument`. This module
is the single typed adapter for the dictionary-based CRUD interface.
"""

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import NotRequired, TypedDict

from app.elan.domain import AlignableAnnotation, EafDocument, ReferenceAnnotation
from app.utils.file_processing import make_path_relative_to_projects


class PersistedMedia(TypedDict):
    """Media fields accepted by the relational persistence layer."""

    media_url: str
    mime_type: str
    relative_media_url: str | None


class PersistedAnnotation(TypedDict):
    """Annotation fields accepted by the relational persistence layer."""

    annotation_id: str
    annotation_value: str
    start_time: Decimal | None
    end_time: Decimal | None
    annotation_kind: str
    annotation_ref: NotRequired[str]
    previous_annotation: NotRequired[str | None]
    cv_entry_ref: NotRequired[str | None]
    ext_ref: NotRequired[str | None]


class PersistedTier(TypedDict):
    """Tier fields accepted by the relational persistence layer."""

    tier_name: str
    parent_tier_name: str | None
    linguistic_type_ref: str
    eaf_attributes: dict[str, str]
    annotations: list[PersistedAnnotation]
    tier_id: NotRequired[int]


class PersistedEafFile(TypedDict):
    """EAF fields accepted by the relational persistence layer."""

    filename: str
    file_path: str
    file_size: int
    last_modified: datetime
    sha256: str
    raw_xml: bytes
    tiers: list[PersistedTier]
    time_slots: dict[str, int | None]
    media: list[PersistedMedia]


def _resolved_times(
    document: EafDocument,
) -> dict[str, tuple[Decimal | None, Decimal | None]]:
    """Resolve inherited reference-annotation times without inventing zeroes."""
    annotations = {item.annotation_id: item for item in document.annotations}
    resolved: dict[str, tuple[Decimal | None, Decimal | None]] = {}

    def resolve(annotation_id: str) -> tuple[Decimal | None, Decimal | None]:
        if annotation_id in resolved:
            return resolved[annotation_id]
        annotation = annotations[annotation_id]
        result: tuple[Decimal | None, Decimal | None]
        if isinstance(annotation, AlignableAnnotation):
            if annotation.start_seconds is None or annotation.end_seconds is None:
                result = (None, None)
            else:
                result = (annotation.start_seconds, annotation.end_seconds)
        else:
            result = resolve(annotation.annotation_ref)
        resolved[annotation_id] = result
        return result

    for annotation_id in annotations:
        resolve(annotation_id)
    return resolved


def document_to_persistence(
    document: EafDocument,
    *,
    persistence_path: Path | None = None,
    modified_at: datetime | None = None,
) -> PersistedEafFile:
    """Adapt a validated typed document to the existing CRUD contract."""
    path = persistence_path or document.source_path
    timestamp = modified_at or document.source_modified_at
    if path is None or timestamp is None:
        raise ValueError("persistence requires a document parsed from a file path")
    times = _resolved_times(document)
    tiers: list[PersistedTier] = []
    for tier in document.tiers:
        annotations: list[PersistedAnnotation] = []
        for annotation in tier.annotations:
            start_time, end_time = times[annotation.annotation_id]
            projected = PersistedAnnotation(
                annotation_id=annotation.annotation_id,
                annotation_value=annotation.value,
                annotation_kind=(
                    "alignable"
                    if isinstance(annotation, AlignableAnnotation)
                    else "reference"
                ),
                start_time=start_time,
                end_time=end_time,
                cv_entry_ref=annotation.cv_entry_ref,
                ext_ref=annotation.ext_ref,
            )
            if isinstance(annotation, ReferenceAnnotation):
                projected["annotation_ref"] = annotation.annotation_ref
                projected["previous_annotation"] = annotation.previous_annotation
            annotations.append(projected)
        tiers.append(
            PersistedTier(
                tier_name=tier.tier_id,
                parent_tier_name=tier.parent_ref,
                linguistic_type_ref=tier.linguistic_type_ref,
                eaf_attributes=dict(tier.attributes),
                annotations=annotations,
            )
        )

    return PersistedEafFile(
        filename=path.name,
        file_path=make_path_relative_to_projects(str(path)),
        file_size=len(document.raw_xml),
        last_modified=timestamp,
        sha256=document.sha256,
        raw_xml=document.raw_xml,
        tiers=tiers,
        time_slots=dict(document.time_values_ms),
        media=[
            PersistedMedia(
                media_url=media.media_url,
                mime_type=media.mime_type,
                relative_media_url=media.relative_media_url,
            )
            for media in document.header.media_descriptors
        ],
    )
