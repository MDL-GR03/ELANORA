"""Researcher-facing semantic comparisons between validated EAF documents."""

from dataclasses import dataclass
from enum import StrEnum

from app.elan.domain import (
    AlignableAnnotation,
    EafAnnotation,
    EafDocument,
    ReferenceAnnotation,
)


class AnnotationChangeKind(StrEnum):
    """Kinds of annotation changes a researcher can review."""

    ADDED = "added"
    REMOVED = "removed"
    VALUE_CHANGED = "value_changed"
    TIMING_CHANGED = "timing_changed"
    TIER_CHANGED = "tier_changed"
    REFERENCE_CHANGED = "reference_changed"


@dataclass(frozen=True, slots=True)
class AnnotationSnapshot:
    """The small, meaningful portion of an annotation used in review."""

    annotation_id: str
    tier_id: str
    value: str
    start_ms: int | None
    end_ms: int | None
    annotation_ref: str | None


@dataclass(frozen=True, slots=True)
class AnnotationChange:
    """One semantic difference, independent of XML line layout."""

    annotation_id: str
    kinds: tuple[AnnotationChangeKind, ...]
    before: AnnotationSnapshot | None
    after: AnnotationSnapshot | None

    @property
    def focus_start_ms(self) -> int | None:
        """Return the earliest known time suitable for media seeking."""
        values = [
            item.start_ms
            for item in (self.before, self.after)
            if item is not None and item.start_ms is not None
        ]
        return min(values) if values else None

    @property
    def focus_end_ms(self) -> int | None:
        """Return the latest known time suitable for a review interval."""
        values = [
            item.end_ms
            for item in (self.before, self.after)
            if item is not None and item.end_ms is not None
        ]
        return max(values) if values else None


@dataclass(frozen=True, slots=True)
class EafComparison:
    """A semantic EAF comparison prepared for a review interface."""

    changes: tuple[AnnotationChange, ...]
    before_media_urls: tuple[str, ...]
    after_media_urls: tuple[str, ...]


def _annotation_index(document: EafDocument) -> dict[str, AnnotationSnapshot]:
    direct_times = {
        annotation.annotation_id: (annotation.start_ms, annotation.end_ms)
        for annotation in document.annotations
        if isinstance(annotation, AlignableAnnotation)
    }
    annotation_by_id = {
        annotation.annotation_id: annotation for annotation in document.annotations
    }

    def inherited_times(
        annotation: EafAnnotation, visited: frozenset[str] = frozenset()
    ) -> tuple[int | None, int | None]:
        if isinstance(annotation, AlignableAnnotation):
            return annotation.start_ms, annotation.end_ms
        if annotation.annotation_ref in visited:
            return None, None
        direct = direct_times.get(annotation.annotation_ref)
        if direct is not None:
            return direct
        parent = annotation_by_id.get(annotation.annotation_ref)
        if parent is None:
            return None, None
        return inherited_times(parent, visited | {annotation.annotation_ref})

    result: dict[str, AnnotationSnapshot] = {}
    for tier in document.tiers:
        for annotation in tier.annotations:
            start_ms, end_ms = inherited_times(annotation)
            result[annotation.annotation_id] = AnnotationSnapshot(
                annotation_id=annotation.annotation_id,
                tier_id=tier.tier_id,
                value=annotation.value,
                start_ms=start_ms,
                end_ms=end_ms,
                annotation_ref=(
                    annotation.annotation_ref
                    if isinstance(annotation, ReferenceAnnotation)
                    else None
                ),
            )
    return result


def compare_eaf(before: EafDocument, after: EafDocument) -> EafComparison:
    """Compare annotation meaning without exposing an XML line diff."""
    before_items = _annotation_index(before)
    after_items = _annotation_index(after)
    changes: list[AnnotationChange] = []

    for annotation_id in sorted(before_items.keys() | after_items.keys()):
        old = before_items.get(annotation_id)
        new = after_items.get(annotation_id)
        kinds: tuple[AnnotationChangeKind, ...]
        if old is None:
            kinds = (AnnotationChangeKind.ADDED,)
        elif new is None:
            kinds = (AnnotationChangeKind.REMOVED,)
        else:
            detected: list[AnnotationChangeKind] = []
            if old.value != new.value:
                detected.append(AnnotationChangeKind.VALUE_CHANGED)
            if (old.start_ms, old.end_ms) != (new.start_ms, new.end_ms):
                detected.append(AnnotationChangeKind.TIMING_CHANGED)
            if old.tier_id != new.tier_id:
                detected.append(AnnotationChangeKind.TIER_CHANGED)
            if old.annotation_ref != new.annotation_ref:
                detected.append(AnnotationChangeKind.REFERENCE_CHANGED)
            kinds = tuple(detected)
        if kinds:
            changes.append(
                AnnotationChange(
                    annotation_id=annotation_id,
                    kinds=kinds,
                    before=old,
                    after=new,
                )
            )

    return EafComparison(
        changes=tuple(changes),
        before_media_urls=tuple(
            item.media_url for item in before.header.media_descriptors
        ),
        after_media_urls=tuple(
            item.media_url for item in after.header.media_descriptors
        ),
    )
