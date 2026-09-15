"""Deterministic evaluation of EAF revisions against published protocols.

A validation run is identified by EAF revision, protocol version and validator
release. The release checksum covers exactly the sources that decide an
outcome, listed in ``VALIDATOR_SOURCES``. Changing any of them without
incrementing ``VALIDATOR_VERSION`` stops validation instead of silently changing
what earlier runs meant. Code outside those sources, such as protocol
administration, may change freely.
"""

import hashlib
from collections.abc import Callable, Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from lxml import etree

from app.core.filename_standard import filename_matches
from app.elan.validation import SCHEMA_PATH, validate_eaf
from app.model.enums import ValidationSeverity
from app.model.protocol import ProtocolVersion
from app.schema.protocol import ProtocolRules

VALIDATOR_NAME = "elanora-eaf"
# 2: EXT_REF lists and xsd:boolean "1"/"0" were rejected by semantic validation
#    under release 1, although the EAF 3.0 schema allows both.
# 3: vocabulary, tier metadata, completeness, linguistic-type constraint and
#    filename standard rules. Snapshots without them evaluate exactly as under
#    release 2.
VALIDATOR_VERSION = "3"

_APP_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SOURCES: tuple[Path, ...] = (
    SCHEMA_PATH,
    _APP_ROOT / "elan" / "validation.py",
    _APP_ROOT / "elan" / "xsd_types.py",
    _APP_ROOT / "core" / "filename_standard.py",
    Path(__file__).resolve(),
)


def validator_checksum(
    sources: Sequence[Path] = VALIDATOR_SOURCES, version: str = VALIDATOR_VERSION
) -> str:
    """Fingerprint the sources that decide validation outcomes."""
    digest = hashlib.sha256()
    for source in sources:
        digest.update(source.name.encode("utf-8") + b"\0")
        digest.update(source.read_bytes() + b"\0")
    digest.update(version.encode("ascii"))
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class ProtocolFinding:
    """One deterministic researcher-facing finding from a protocol snapshot."""

    code: str
    severity: ValidationSeverity
    location: str
    message: str
    rule_key: str


class _Evaluation:
    """One document under one snapshot, collecting findings in rule order."""

    def __init__(
        self, root: etree._Element, rules: ProtocolRules, filename: str
    ) -> None:
        self.root = root
        self.rules = rules
        self.filename = filename
        self.findings: list[ProtocolFinding] = []
        self.tiers = _by_id(root.findall("TIER"), "TIER_ID")
        self.types = _by_id(root.findall("LINGUISTIC_TYPE"), "LINGUISTIC_TYPE_ID")
        self.vocabularies = _by_id(root.findall("CONTROLLED_VOCABULARY"), "CV_ID")

    def report(self, code: str, location: str, message: str, rule_key: str) -> None:
        self.findings.append(
            ProtocolFinding(
                code=code,
                severity=self.rules.severity_of(rule_key),
                location=location,
                message=message,
                rule_key=rule_key,
            )
        )

    def present_tiers(
        self, tier_ids: Iterable[str]
    ) -> Iterator[tuple[str, etree._Element]]:
        """Listed tiers found in the document; absent ones are required_tiers' job."""
        for tier_id in tier_ids:
            tier = self.tiers.get(tier_id)
            if tier is not None:
                yield tier_id, tier

    def per_tier(
        self,
        tier_ids: Iterable[str],
        offending: Callable[[etree._Element], bool],
        code: str,
        problem: str,
        rule_key: str,
    ) -> None:
        """One finding per tier, counting offenders and locating the first."""
        for tier_id, tier in self.present_tiers(tier_ids):
            failures = [item for item in _annotations(tier) if offending(item)]
            if failures:
                self.report(
                    code,
                    _annotation_path(tier_id, failures[0]),
                    f"Tier {tier_id!r} has {_count(len(failures), 'annotation')} "
                    + problem,
                    rule_key,
                )


def evaluate_protocol_rules(
    root: etree._Element, rules: ProtocolRules, *, filename: str
) -> tuple[ProtocolFinding, ...]:
    """Evaluate a validated EAF document and its filename against a snapshot."""
    evaluation = _Evaluation(root, rules, filename)
    for family in (
        _structure_rules,
        _media_rules,
        _vocabulary_rules,
        _tier_metadata_rules,
        _completeness_rules,
        _constraint_rules,
        _filename_rules,
    ):
        family(evaluation)
    return tuple(evaluation.findings)


def _structure_rules(ev: _Evaluation) -> None:
    rules = ev.rules
    for tier_id in rules.required_tiers:
        if tier_id not in ev.tiers:
            ev.report(
                "protocol.required_tier_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required tier {tier_id!r} is missing",
                "required_tiers",
            )
    for tier_id, tier in ev.present_tiers(rules.tier_parents):
        required_parent = rules.tier_parents[tier_id]
        if tier.get("PARENT_REF") != required_parent:
            ev.report(
                "protocol.tier_parent_mismatch",
                _tier_path(tier_id),
                f"Tier {tier_id!r} must have parent {required_parent!r}",
                "tier_parents",
            )
    for tier_id, tier in ev.present_tiers(rules.tier_linguistic_types):
        required_type = rules.tier_linguistic_types[tier_id]
        if tier.get("LINGUISTIC_TYPE_REF") != required_type:
            ev.report(
                "protocol.tier_linguistic_type_mismatch",
                _tier_path(tier_id),
                f"Tier {tier_id!r} must use linguistic type {required_type!r}",
                "tier_linguistic_types",
            )
    for vocabulary_id in rules.required_controlled_vocabularies:
        if vocabulary_id not in ev.vocabularies:
            ev.report(
                "protocol.required_vocabulary_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required controlled vocabulary {vocabulary_id!r} is missing",
                "required_controlled_vocabularies",
            )


def _media_rules(ev: _Evaluation) -> None:
    media = ev.root.findall("HEADER/MEDIA_DESCRIPTOR")
    if ev.rules.media_required and not media:
        ev.report(
            "protocol.media_required",
            "/ANNOTATION_DOCUMENT/HEADER",
            "At least one media descriptor is required",
            "media_required",
        )
    allowed_mime_types = set(ev.rules.allowed_media_mime_types)
    if not allowed_mime_types:
        return
    for descriptor in media:
        mime_type = descriptor.get("MIME_TYPE", "")
        if mime_type not in allowed_mime_types:
            ev.report(
                "protocol.media_mime_type_forbidden",
                ev.root.getroottree().getpath(descriptor),
                f"Media MIME type {mime_type!r} is not permitted",
                "allowed_media_mime_types",
            )


def _vocabulary_rules(ev: _Evaluation) -> None:
    for tier_id, tier in ev.present_tiers(ev.rules.vocabulary_tiers):
        type_id = tier.get("LINGUISTIC_TYPE_REF", "")
        linguistic_type = ev.types.get(type_id)
        cv_id = (
            None
            if linguistic_type is None
            else linguistic_type.get("CONTROLLED_VOCABULARY_REF")
        )
        vocabulary = ev.vocabularies.get(cv_id or "")
        if vocabulary is None:
            ev.report(
                "protocol.tier_without_vocabulary",
                _tier_path(tier_id),
                f"Tier {tier_id!r} must use a controlled vocabulary, but its "
                f"linguistic type {type_id!r} has none",
                "vocabulary_tiers",
            )
            continue
        entry_ids = {entry.get("CVE_ID") for entry in vocabulary.iter("CV_ENTRY_ML")}
        values = {value.text or "" for value in vocabulary.iter("CVE_VALUE")}
        ev.per_tier(
            [tier_id],
            lambda item, entry_ids=entry_ids, values=values: (
                item.get("CVE_REF") not in entry_ids
                if item.get("CVE_REF") is not None
                else _value(item) not in values
            ),
            "protocol.annotation_outside_vocabulary",
            f"not taken from controlled vocabulary {cv_id!r}",
            "vocabulary_tiers",
        )
    for cv_id, languages in ev.rules.vocabulary_languages.items():
        vocabulary = ev.vocabularies.get(cv_id)
        if vocabulary is None:
            continue
        entries = vocabulary.findall("CV_ENTRY_ML")
        for language in languages:
            lacking = [
                entry
                for entry in entries
                if not any(
                    value.get("LANG_REF") == language and (value.text or "").strip()
                    for value in entry.findall("CVE_VALUE")
                )
            ]
            if lacking:
                ev.report(
                    "protocol.vocabulary_value_language_missing",
                    f"/ANNOTATION_DOCUMENT/CONTROLLED_VOCABULARY[@CV_ID='{cv_id}']"
                    f"/CV_ENTRY_ML[@CVE_ID='{lacking[0].get('CVE_ID')}']",
                    f"Controlled vocabulary {cv_id!r} has "
                    f"{_count(len(lacking), 'entry', 'entries')} without a value "
                    f"in language {language!r}",
                    "vocabulary_languages",
                )


def _tier_metadata_rules(ev: _Evaluation) -> None:
    for rule_key, tier_ids, attribute, label in (
        ("participant_tiers", ev.rules.participant_tiers, "PARTICIPANT", "participant"),
        ("annotator_tiers", ev.rules.annotator_tiers, "ANNOTATOR", "annotator"),
    ):
        for tier_id, tier in ev.present_tiers(tier_ids):
            if not (tier.get(attribute) or "").strip():
                ev.report(
                    f"protocol.tier_{label}_missing",
                    _tier_path(tier_id),
                    f"Tier {tier_id!r} must name its {label}",
                    rule_key,
                )
    for tier_id, tier in ev.present_tiers(ev.rules.tier_languages):
        language = ev.rules.tier_languages[tier_id]
        if tier.get("LANG_REF") != language:
            ev.report(
                "protocol.tier_language_mismatch",
                _tier_path(tier_id),
                f"Tier {tier_id!r} must declare content language {language!r}",
                "tier_languages",
            )


def _completeness_rules(ev: _Evaluation) -> None:
    ev.per_tier(
        ev.rules.non_empty_tiers,
        lambda item: not _value(item).strip(),
        "protocol.empty_annotation_values",
        "without a value",
        "non_empty_tiers",
    )
    time_values = {
        slot.get("TIME_SLOT_ID"): slot.get("TIME_VALUE")
        for slot in ev.root.findall("TIME_ORDER/TIME_SLOT")
    }
    ev.per_tier(
        ev.rules.time_aligned_tiers,
        # Reference annotations have no time slots of their own, so they count too.
        lambda item: (
            time_values.get(item.get("TIME_SLOT_REF1")) is None
            or time_values.get(item.get("TIME_SLOT_REF2")) is None
        ),
        "protocol.unaligned_annotations",
        "not aligned to media time",
        "time_aligned_tiers",
    )


def _constraint_rules(ev: _Evaluation) -> None:
    for type_id, stereotype in ev.rules.linguistic_type_constraints.items():
        linguistic_type = ev.types.get(type_id)
        if linguistic_type is None:
            ev.report(
                "protocol.linguistic_type_missing",
                "/ANNOTATION_DOCUMENT",
                f"Linguistic type {type_id!r} is missing",
                "linguistic_type_constraints",
            )
            continue
        actual = linguistic_type.get("CONSTRAINTS") or "none"
        if actual != stereotype:
            ev.report(
                "protocol.linguistic_type_constraint_mismatch",
                "/ANNOTATION_DOCUMENT/LINGUISTIC_TYPE"
                f"[@LINGUISTIC_TYPE_ID='{type_id}']",
                f"Linguistic type {type_id!r} must have {_constraint(stereotype)}, "
                f"not {_constraint(actual)}",
                "linguistic_type_constraints",
            )


def _filename_rules(ev: _Evaluation) -> None:
    standard = ev.rules.filename_standard
    if standard is None:
        return
    if not filename_matches(
        standard.pattern, standard.matcher_components(), ev.filename
    ):
        ev.report(
            "protocol.filename_not_compliant",
            "filename",
            f"Filename {PurePosixPath(ev.filename).name!r} does not follow the "
            f"naming standard {standard.name!r} ({standard.pattern})",
            "filename_standard",
        )


def validate_content_against_protocol(
    content: bytes, version: ProtocolVersion, *, filename: str
) -> tuple[ProtocolFinding, ...]:
    """Validate EAF structure and apply one published protocol snapshot."""
    root = validate_eaf(content)
    return evaluate_protocol_rules(
        root, ProtocolRules.model_validate(version.rules), filename=filename
    )


def blocking_findings(
    findings: Sequence[ProtocolFinding],
) -> tuple[ProtocolFinding, ...]:
    """Findings that refuse an upload, fail a run or prevent acceptance.

    Warnings are recorded and shown to reviewers but never block. Every place
    that turns findings into a decision must use this, so a warning cannot
    block in one path while passing in another.
    """
    return tuple(
        finding for finding in findings if finding.severity == ValidationSeverity.ERROR
    )


def _by_id(
    elements: Iterable[etree._Element], attribute: str
) -> dict[str, etree._Element]:
    return {
        identifier: element
        for element in elements
        if (identifier := element.get(attribute)) is not None
    }


def _annotations(tier: etree._Element) -> list[etree._Element]:
    """The alignable or reference element of each annotation, in document order."""
    return [child for annotation in tier.findall("ANNOTATION") for child in annotation]


def _tier_path(tier_id: str) -> str:
    return f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']"


def _annotation_path(tier_id: str, annotation: etree._Element) -> str:
    return (
        f"{_tier_path(tier_id)}/ANNOTATION/{annotation.tag}"
        f"[@ANNOTATION_ID='{annotation.get('ANNOTATION_ID')}']"
    )


def _value(annotation: etree._Element) -> str:
    value = annotation.find("ANNOTATION_VALUE")
    return "" if value is None else value.text or ""


def _count(count: int, singular: str, plural: str | None = None) -> str:
    return f"{count} {singular if count == 1 else plural or singular + 's'}"


def _constraint(stereotype: str) -> str:
    return "no constraint" if stereotype == "none" else repr(stereotype)
