"""Secure structural and semantic validation for EAF 3.x documents."""

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
from itertools import pairwise
from pathlib import Path
from typing import Final, cast

from lxml import etree

ROOT_TAG: Final = "ANNOTATION_DOCUMENT"
SUPPORTED_FORMATS: Final = frozenset({"2.7", "2.8", "3.0"})
SCHEMA_PATH: Final = Path(__file__).parent / "schemas" / "EAFv3.0.xsd"
MAX_SCHEMA_ISSUES: Final = 100


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """One actionable EAF validation failure."""

    code: str
    message: str
    location: str

    def __str__(self) -> str:
        """Render the issue for logs and API error summaries."""
        return f"{self.code} at {self.location}: {self.message}"


class EafValidationError(ValueError):
    """Raised when XML is unsafe, malformed, or violates EAF invariants."""

    def __init__(self, issues: tuple[ValidationIssue, ...]) -> None:
        """Create an error containing every issue found in one validation pass."""
        self.issues = issues
        super().__init__("; ".join(str(issue) for issue in issues))


def secure_xml_parser() -> etree.XMLParser:
    """Build an XML parser that cannot resolve external resources."""
    return etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        recover=False,
        huge_tree=False,
        remove_blank_text=False,
    )


@lru_cache(maxsize=1)
def _eaf_schema() -> etree.XMLSchema:
    """Load the vendored official EAF 3.0 schema once per process."""
    return etree.XMLSchema(file=str(SCHEMA_PATH))


def _validate_schema(root: etree._Element, issues: list[ValidationIssue]) -> None:
    """Collect official XML Schema failures without network access."""
    schema = _eaf_schema()
    if schema.validate(root):
        return
    issues.extend(
        _issue("xsd_validation", entry.message, f"line {entry.line}")
        for entry in schema.error_log[:MAX_SCHEMA_ISSUES]
    )


def _issue(
    code: str, message: str, location: str = "/ANNOTATION_DOCUMENT"
) -> ValidationIssue:
    return ValidationIssue(code=code, message=message, location=location)


def _required(
    element: etree._Element,
    attribute: str,
    issues: list[ValidationIssue],
    *,
    allow_empty: bool = False,
) -> str | None:
    value = element.get(attribute)
    if value is None or (not allow_empty and not value.strip()):
        issues.append(
            _issue(
                "required_attribute",
                f"{attribute} is required",
                element.getroottree().getpath(element),
            )
        )
        return None
    return cast("str", value)


def _duplicates(values: list[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}


def _validate_parent_cycles(
    parent_by_tier: dict[str, str], issues: list[ValidationIssue]
) -> None:
    for tier_id in parent_by_tier:
        visited: set[str] = set()
        current: str | None = tier_id
        while current is not None:
            if current in visited:
                issues.append(
                    _issue(
                        "tier_cycle",
                        f"tier parent cycle includes {current!r}",
                        f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']",
                    )
                )
                break
            visited.add(current)
            current = parent_by_tier.get(current)


def _validate_annotation_cycles(
    annotation_refs: dict[str, str], issues: list[ValidationIssue]
) -> None:
    for annotation_id in annotation_refs:
        visited: set[str] = set()
        current: str | None = annotation_id
        while current is not None:
            if current in visited:
                issues.append(
                    _issue(
                        "annotation_cycle",
                        f"annotation reference cycle includes {current!r}",
                        f"//*[@ANNOTATION_ID='{annotation_id}']",
                    )
                )
                break
            visited.add(current)
            current = annotation_refs.get(current)


def validate_eaf(content: bytes) -> etree._Element:
    """Parse and validate an EAF payload.

    Validation is deliberately offline and deterministic. It combines secure XML
    parsing with the cross-reference and semantic constraints that XML Schema
    alone cannot express.
    """
    try:
        root = etree.fromstring(content, parser=secure_xml_parser())
    except etree.XMLSyntaxError as exc:
        raise EafValidationError(
            (_issue("xml_syntax", "XML is not well formed", f"line {exc.lineno}"),)
        ) from exc

    if root.getroottree().docinfo.doctype:
        raise EafValidationError(
            (
                _issue(
                    "doctype_forbidden",
                    "document type declarations are not allowed",
                    "/",
                ),
            )
        )

    issues: list[ValidationIssue] = []
    if root.tag != ROOT_TAG:
        issues.append(
            _issue("wrong_root", f"expected {ROOT_TAG}, found {root.tag!r}", "/")
        )
        raise EafValidationError(tuple(issues))

    _validate_schema(root, issues)

    _required(root, "AUTHOR", issues, allow_empty=True)
    for attribute in ("DATE", "FORMAT", "VERSION"):
        _required(root, attribute, issues)
    format_version = root.get("FORMAT")
    if format_version and format_version not in SUPPORTED_FORMATS:
        issues.append(
            _issue("unsupported_format", f"FORMAT {format_version!r} is not supported")
        )

    headers = root.findall("HEADER")
    time_orders = root.findall("TIME_ORDER")
    if len(headers) != 1:
        issues.append(_issue("header_count", "exactly one HEADER is required"))
    if len(time_orders) != 1:
        issues.append(_issue("time_order_count", "exactly one TIME_ORDER is required"))
    if issues and (not headers or not time_orders):
        raise EafValidationError(tuple(issues))

    header = headers[0]
    if header.get("TIME_UNITS") != "milliseconds":
        issues.append(
            _issue(
                "time_units",
                "TIME_UNITS must be 'milliseconds'",
                "/ANNOTATION_DOCUMENT/HEADER",
            )
        )

    time_slots = time_orders[0].findall("TIME_SLOT")
    time_slot_ids = [
        value
        for slot in time_slots
        if (value := _required(slot, "TIME_SLOT_ID", issues))
    ]
    for duplicate in _duplicates(time_slot_ids):
        issues.append(
            _issue(
                "duplicate_time_slot",
                f"duplicate TIME_SLOT_ID {duplicate!r}",
                "/ANNOTATION_DOCUMENT/TIME_ORDER",
            )
        )
    time_slot_id_set = set(time_slot_ids)
    time_values: dict[str, int | None] = {}
    for slot in time_slots:
        slot_id = slot.get("TIME_SLOT_ID")
        raw_value = slot.get("TIME_VALUE")
        if not slot_id:
            continue
        if raw_value is None:
            time_values[slot_id] = None
            continue
        try:
            parsed = int(raw_value)
            if parsed < 0:
                raise ValueError
            time_values[slot_id] = parsed
        except ValueError:
            issues.append(
                _issue(
                    "invalid_time",
                    f"TIME_VALUE for {slot_id!r} must be a non-negative integer",
                    time_orders[0].getroottree().getpath(slot),
                )
            )

    linguistic_types = root.findall("LINGUISTIC_TYPE")
    linguistic_type_ids = [
        value
        for item in linguistic_types
        if (value := _required(item, "LINGUISTIC_TYPE_ID", issues))
    ]
    for duplicate in _duplicates(linguistic_type_ids):
        issues.append(
            _issue(
                "duplicate_linguistic_type",
                f"duplicate LINGUISTIC_TYPE_ID {duplicate!r}",
            )
        )
    linguistic_type_id_set = set(linguistic_type_ids)

    vocabulary_ids = {
        item.get("CV_ID")
        for item in root.findall("CONTROLLED_VOCABULARY")
        if item.get("CV_ID")
    }
    language_ids = {
        item.get("LANG_ID") for item in root.findall("LANGUAGE") if item.get("LANG_ID")
    }
    external_ref_ids = {
        item.get("EXT_REF_ID")
        for item in root.findall("EXTERNAL_REF")
        if item.get("EXT_REF_ID")
    }
    vocabulary_entries: dict[str, set[str]] = {}
    for vocabulary in root.findall("CONTROLLED_VOCABULARY"):
        cv_id = vocabulary.get("CV_ID")
        if cv_id:
            vocabulary_entries[cv_id] = {
                entry.get("CVE_ID")
                for entry in vocabulary.findall("CV_ENTRY_ML")
                if entry.get("CVE_ID")
            }
        for value in vocabulary.findall("./CV_ENTRY_ML/CVE_VALUE"):
            lang_ref = value.get("LANG_REF")
            if lang_ref and lang_ref not in language_ids:
                issues.append(
                    _issue(
                        "unknown_language",
                        f"CVE_VALUE refers to unknown language {lang_ref!r}",
                        value.getroottree().getpath(value),
                    )
                )

    cv_by_linguistic_type: dict[str, str] = {}
    alignable_by_linguistic_type: dict[str, bool] = {}
    for linguistic_type in linguistic_types:
        type_id = linguistic_type.get("LINGUISTIC_TYPE_ID")
        if not type_id:
            continue
        cv_ref = linguistic_type.get("CONTROLLED_VOCABULARY_REF")
        if cv_ref:
            cv_by_linguistic_type[type_id] = cv_ref
            if cv_ref not in vocabulary_ids:
                issues.append(
                    _issue(
                        "unknown_vocabulary",
                        f"linguistic type refers to unknown vocabulary {cv_ref!r}",
                        linguistic_type.getroottree().getpath(linguistic_type),
                    )
                )
        alignable_by_linguistic_type[type_id] = (
            linguistic_type.get("TIME_ALIGNABLE", "true").lower() == "true"
        )

    tier_ids: list[str] = []
    parent_by_tier: dict[str, str] = {}
    annotation_ids: list[str] = []
    annotation_refs: dict[str, str] = {}
    previous_annotation_refs: dict[str, str] = {}
    annotation_tiers: dict[str, str] = {}
    annotation_elements: list[etree._Element] = []
    for tier in root.findall("TIER"):
        tier_id = _required(tier, "TIER_ID", issues)
        type_ref = _required(tier, "LINGUISTIC_TYPE_REF", issues)
        if tier_id:
            tier_ids.append(tier_id)
        if type_ref and type_ref not in linguistic_type_id_set:
            issues.append(
                _issue(
                    "unknown_linguistic_type",
                    f"tier refers to unknown linguistic type {type_ref!r}",
                    tier.getroottree().getpath(tier),
                )
            )
        parent_ref = tier.get("PARENT_REF")
        if tier_id and parent_ref:
            parent_by_tier[tier_id] = parent_ref
        lang_ref = tier.get("LANG_REF")
        if lang_ref and lang_ref not in language_ids:
            issues.append(
                _issue(
                    "unknown_language",
                    f"tier refers to unknown language {lang_ref!r}",
                    tier.getroottree().getpath(tier),
                )
            )

        direct_annotations = tier.findall("./ANNOTATION/*")
        annotation_kinds = {item.tag for item in direct_annotations}
        if len(annotation_kinds) > 1:
            issues.append(
                _issue(
                    "mixed_annotation_kinds",
                    "a tier cannot mix alignable and reference annotations",
                    tier.getroottree().getpath(tier),
                )
            )
        expected_alignable = alignable_by_linguistic_type.get(type_ref or "")
        if "ALIGNABLE_ANNOTATION" in annotation_kinds and expected_alignable is False:
            issues.append(
                _issue(
                    "alignment_mismatch",
                    "non-time-alignable linguistic type contains alignable annotations",
                    tier.getroottree().getpath(tier),
                )
            )
        if "REF_ANNOTATION" in annotation_kinds and expected_alignable is True:
            issues.append(
                _issue(
                    "alignment_mismatch",
                    "time-alignable linguistic type contains reference annotations",
                    tier.getroottree().getpath(tier),
                )
            )

        for annotation in direct_annotations:
            annotation_elements.append(annotation)
            annotation_id = _required(annotation, "ANNOTATION_ID", issues)
            if annotation_id:
                annotation_ids.append(annotation_id)
                if tier_id:
                    annotation_tiers[annotation_id] = tier_id
            values = annotation.findall("ANNOTATION_VALUE")
            if len(values) != 1:
                issues.append(
                    _issue(
                        "annotation_value_count",
                        "exactly one ANNOTATION_VALUE is required",
                        annotation.getroottree().getpath(annotation),
                    )
                )
            if annotation.tag == "ALIGNABLE_ANNOTATION":
                start_ref = _required(annotation, "TIME_SLOT_REF1", issues)
                end_ref = _required(annotation, "TIME_SLOT_REF2", issues)
                for reference in (start_ref, end_ref):
                    if reference and reference not in time_slot_id_set:
                        issues.append(
                            _issue(
                                "unknown_time_slot",
                                f"annotation refers to unknown time slot {reference!r}",
                                annotation.getroottree().getpath(annotation),
                            )
                        )
                if start_ref in time_values and end_ref in time_values:
                    start = time_values[start_ref]
                    end = time_values[end_ref]
                    if start is not None and end is not None and end < start:
                        issues.append(
                            _issue(
                                "negative_duration",
                                "annotation end precedes its start",
                                annotation.getroottree().getpath(annotation),
                            )
                        )
            elif annotation.tag == "REF_ANNOTATION":
                annotation_ref = _required(annotation, "ANNOTATION_REF", issues)
                if annotation_id and annotation_ref:
                    annotation_refs[annotation_id] = annotation_ref
                previous_ref = annotation.get("PREVIOUS_ANNOTATION")
                if annotation_id and previous_ref:
                    previous_annotation_refs[annotation_id] = previous_ref
            else:
                issues.append(
                    _issue(
                        "unknown_annotation_kind",
                        f"unsupported annotation element {annotation.tag!r}",
                        annotation.getroottree().getpath(annotation),
                    )
                )

            ext_ref = annotation.get("EXT_REF")
            if ext_ref and ext_ref not in external_ref_ids:
                issues.append(
                    _issue(
                        "unknown_external_ref",
                        f"annotation refers to unknown external reference {ext_ref!r}",
                        annotation.getroottree().getpath(annotation),
                    )
                )
            cv_entry_ref = annotation.get("CVE_REF")
            if cv_entry_ref and type_ref:
                cv_id = cv_by_linguistic_type.get(type_ref)
                if not cv_id or cv_entry_ref not in vocabulary_entries.get(
                    cv_id, set()
                ):
                    issues.append(
                        _issue(
                            "unknown_cv_entry",
                            f"annotation refers to CV entry {cv_entry_ref!r} outside its linguistic type vocabulary",
                            annotation.getroottree().getpath(annotation),
                        )
                    )

    for duplicate in _duplicates(tier_ids):
        issues.append(_issue("duplicate_tier", f"duplicate TIER_ID {duplicate!r}"))
    tier_id_set = set(tier_ids)
    for tier_id, parent_ref in parent_by_tier.items():
        if parent_ref not in tier_id_set:
            issues.append(
                _issue(
                    "unknown_parent_tier",
                    f"tier {tier_id!r} refers to unknown parent {parent_ref!r}",
                )
            )
    _validate_parent_cycles(parent_by_tier, issues)

    for duplicate in _duplicates(annotation_ids):
        issues.append(
            _issue("duplicate_annotation", f"duplicate ANNOTATION_ID {duplicate!r}")
        )
    annotation_id_set = set(annotation_ids)
    for annotation_id, annotation_ref in annotation_refs.items():
        if annotation_ref not in annotation_id_set:
            issues.append(
                _issue(
                    "unknown_annotation_ref",
                    f"annotation {annotation_id!r} refers to unknown annotation {annotation_ref!r}",
                )
            )
    _validate_annotation_cycles(annotation_refs, issues)

    for annotation_id, previous_ref in previous_annotation_refs.items():
        if previous_ref not in annotation_id_set:
            issues.append(
                _issue(
                    "unknown_previous_annotation",
                    f"annotation {annotation_id!r} refers to unknown previous annotation {previous_ref!r}",
                )
            )
        elif annotation_tiers.get(previous_ref) != annotation_tiers.get(annotation_id):
            issues.append(
                _issue(
                    "previous_annotation_tier",
                    "PREVIOUS_ANNOTATION must refer to an annotation on the same tier",
                    f"//*[@ANNOTATION_ID='{annotation_id}']",
                )
            )

    # A tier is one annotation track: fully aligned annotations may meet at a
    # boundary, but overlapping intervals on that track are invalid.
    for tier in root.findall("TIER"):
        intervals: list[tuple[int, int, str]] = []
        for annotation in tier.findall("./ANNOTATION/ALIGNABLE_ANNOTATION"):
            start = time_values.get(annotation.get("TIME_SLOT_REF1", ""))
            end = time_values.get(annotation.get("TIME_SLOT_REF2", ""))
            if start is not None and end is not None:
                intervals.append((start, end, annotation.get("ANNOTATION_ID", "")))
        intervals.sort()
        for previous, current in pairwise(intervals):
            if current[0] < previous[1]:
                issues.append(
                    _issue(
                        "overlapping_annotations",
                        f"annotations {previous[2]!r} and {current[2]!r} overlap on one tier",
                        tier.getroottree().getpath(tier),
                    )
                )

    if issues:
        raise EafValidationError(tuple(issues))
    return root
