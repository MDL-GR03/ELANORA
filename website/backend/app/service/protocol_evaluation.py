"""Deterministic evaluation of EAF revisions against published protocols.

A validation run is identified by EAF revision, protocol version and validator
release. The release checksum covers exactly the sources that decide an
outcome, listed in ``VALIDATOR_SOURCES``. Changing any of them without
incrementing ``VALIDATOR_VERSION`` stops validation instead of silently changing
what earlier runs meant. Code outside those sources, such as protocol
administration, may change freely.
"""

import hashlib
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from lxml import etree

from app.elan.validation import SCHEMA_PATH, validate_eaf
from app.model.enums import ValidationSeverity
from app.model.protocol import ProtocolVersion
from app.schema.protocol import ProtocolRules

VALIDATOR_NAME = "elanora-eaf"
# 2: EXT_REF lists and xsd:boolean "1"/"0" were rejected by semantic validation
#    under release 1, although the EAF 3.0 schema allows both.
VALIDATOR_VERSION = "2"

_APP_ROOT = Path(__file__).resolve().parents[1]
VALIDATOR_SOURCES: tuple[Path, ...] = (
    SCHEMA_PATH,
    _APP_ROOT / "elan" / "validation.py",
    _APP_ROOT / "elan" / "xsd_types.py",
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


def evaluate_protocol_rules(
    root: etree._Element, rules: ProtocolRules
) -> tuple[ProtocolFinding, ...]:
    """Evaluate a validated EAF document against immutable protocol rules."""
    findings: list[ProtocolFinding] = []

    def error(code: str, location: str, message: str, rule_key: str) -> None:
        findings.append(
            ProtocolFinding(
                code=code,
                severity=rules.severity_of(rule_key),
                location=location,
                message=message,
                rule_key=rule_key,
            )
        )

    tiers = {
        tier_id: tier
        for tier in root.findall("TIER")
        if (tier_id := tier.get("TIER_ID")) is not None
    }
    tier_ids = set(tiers)
    for tier_id in rules.required_tiers:
        if tier_id not in tier_ids:
            error(
                "protocol.required_tier_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required tier {tier_id!r} is missing",
                "required_tiers",
            )
    for tier_id, required_parent in rules.tier_parents.items():
        tier = tiers.get(tier_id)
        if tier is not None and tier.get("PARENT_REF") != required_parent:
            error(
                "protocol.tier_parent_mismatch",
                f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']",
                f"Tier {tier_id!r} must have parent {required_parent!r}",
                "tier_parents",
            )
    for tier_id, required_type in rules.tier_linguistic_types.items():
        tier = tiers.get(tier_id)
        if tier is not None and tier.get("LINGUISTIC_TYPE_REF") != required_type:
            error(
                "protocol.tier_linguistic_type_mismatch",
                f"/ANNOTATION_DOCUMENT/TIER[@TIER_ID='{tier_id}']",
                f"Tier {tier_id!r} must use linguistic type {required_type!r}",
                "tier_linguistic_types",
            )
    vocabulary_ids = {
        item.get("CV_ID")
        for item in root.findall("CONTROLLED_VOCABULARY")
        if item.get("CV_ID")
    }
    for vocabulary_id in rules.required_controlled_vocabularies:
        if vocabulary_id not in vocabulary_ids:
            error(
                "protocol.required_vocabulary_missing",
                "/ANNOTATION_DOCUMENT",
                f"Required controlled vocabulary {vocabulary_id!r} is missing",
                "required_controlled_vocabularies",
            )
    media = root.findall("HEADER/MEDIA_DESCRIPTOR")
    if rules.media_required and not media:
        error(
            "protocol.media_required",
            "/ANNOTATION_DOCUMENT/HEADER",
            "At least one media descriptor is required",
            "media_required",
        )
    allowed_mime_types = set(rules.allowed_media_mime_types)
    if allowed_mime_types:
        for descriptor in media:
            mime_type = descriptor.get("MIME_TYPE", "")
            if mime_type not in allowed_mime_types:
                error(
                    "protocol.media_mime_type_forbidden",
                    root.getroottree().getpath(descriptor),
                    f"Media MIME type {mime_type!r} is not permitted",
                    "allowed_media_mime_types",
                )
    return tuple(findings)


def validate_content_against_protocol(
    content: bytes, version: ProtocolVersion
) -> tuple[ProtocolFinding, ...]:
    """Validate EAF structure and apply one published protocol snapshot."""
    root = validate_eaf(content)
    return evaluate_protocol_rules(root, ProtocolRules.model_validate(version.rules))


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
