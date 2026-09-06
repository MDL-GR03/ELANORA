"""Typed, lossless ELAN Annotation Format support."""

from app.elan.comparison import (
    AnnotationChange,
    AnnotationChangeKind,
    AnnotationSnapshot,
    EafComparison,
    compare_eaf,
)
from app.elan.domain import (
    AlignableAnnotation,
    EafDocument,
    EafHeader,
    EafTier,
    ElementSnapshot,
    MediaDescriptor,
    ReferenceAnnotation,
)
from app.elan.legacy import LegacyEafFile, document_to_legacy
from app.elan.parser import parse_eaf, parse_eaf_path
from app.elan.validation import EafValidationError, ValidationIssue, validate_eaf

__all__ = [
    "AlignableAnnotation",
    "AnnotationChange",
    "AnnotationChangeKind",
    "AnnotationSnapshot",
    "EafComparison",
    "EafDocument",
    "EafHeader",
    "EafTier",
    "EafValidationError",
    "ElementSnapshot",
    "LegacyEafFile",
    "MediaDescriptor",
    "ReferenceAnnotation",
    "ValidationIssue",
    "compare_eaf",
    "document_to_legacy",
    "parse_eaf",
    "parse_eaf_path",
    "validate_eaf",
]
