"""Vocabulary, tier metadata, completeness and linguistic-type constraint rules.

Each test starts from a fixture that satisfies the rule, then breaks exactly the
property the rule protects, so a rule that reports nothing cannot pass.
"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.elan.validation import validate_eaf
from app.model.enums import ValidationSeverity
from app.schema.protocol import ProtocolRules
from app.service.protocol_evaluation import ProtocolFinding, evaluate_protocol_rules

FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
).read_bytes()
BOTH_TIERS = ["translation", "utterance"]


def _findings(content: bytes, **rules: object) -> tuple[ProtocolFinding, ...]:
    return evaluate_protocol_rules(
        validate_eaf(content), ProtocolRules.model_validate(rules)
    )


def _replace(old: bytes, new: bytes, content: bytes = FIXTURE) -> bytes:
    assert old in content, f"fixture no longer contains {old!r}"
    return content.replace(old, new, 1)


def _codes(findings: tuple[ProtocolFinding, ...]) -> list[str]:
    return [finding.code for finding in findings]


def _second_utterance(value: bytes, cve_ref: bytes = b"") -> bytes:
    """Add another aligned annotation on the utterance tier."""
    content = _replace(
        b'<TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="2500"/>',
        b'<TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="2500"/>\n'
        b'        <TIME_SLOT TIME_SLOT_ID="ts3" TIME_VALUE="3000"/>\n'
        b'        <TIME_SLOT TIME_SLOT_ID="ts4" TIME_VALUE="4000"/>',
    )
    return _replace(
        b"        </ANNOTATION>\n    </TIER>",
        b"        </ANNOTATION>\n"
        b'        <ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a3" '
        b'TIME_SLOT_REF1="ts3" TIME_SLOT_REF2="ts4"' + cve_ref + b">"
        b"<ANNOTATION_VALUE>" + value + b"</ANNOTATION_VALUE>"
        b"</ALIGNABLE_ANNOTATION></ANNOTATION>\n    </TIER>",
        content,
    )


# Vocabulary rules ------------------------------------------------------------


def test_annotations_that_use_their_vocabulary_satisfy_the_rule() -> None:
    assert (
        _findings(
            _second_utterance(b"Hello"),
            required_tiers=["utterance"],
            vocabulary_tiers=["utterance"],
        )
        == ()
    )


def test_a_value_outside_the_vocabulary_is_reported_once_per_tier() -> None:
    content = _second_utterance(b"Howdy")
    content = content.replace(b' CVE_REF="cve-greeting"', b"", 1)
    content = content.replace(b"<ANNOTATION_VALUE>Hello<", b"<ANNOTATION_VALUE>Hi<")

    (finding,) = _findings(
        content, required_tiers=["utterance"], vocabulary_tiers=["utterance"]
    )

    assert finding.code == "protocol.annotation_outside_vocabulary"
    assert finding.rule_key == "vocabulary_tiers"
    assert "2 annotations" in finding.message
    assert "greetings" in finding.message
    assert finding.location.endswith("[@ANNOTATION_ID='a1']")


def test_a_vocabulary_tier_whose_type_has_no_vocabulary_is_reported() -> None:
    (finding,) = _findings(
        FIXTURE, required_tiers=BOTH_TIERS, vocabulary_tiers=["translation"]
    )

    assert finding.code == "protocol.tier_without_vocabulary"
    assert "translation-type" in finding.message


def test_vocabulary_entries_need_a_value_in_each_required_language() -> None:
    content = _replace(
        b"        </CV_ENTRY_ML>\n",
        b"        </CV_ENTRY_ML>\n"
        b'        <CV_ENTRY_ML CVE_ID="cve-farewell">'
        b'<CVE_VALUE LANG_REF="en">Goodbye</CVE_VALUE></CV_ENTRY_ML>\n',
    )
    rules = {
        "required_controlled_vocabularies": ["greetings"],
        "vocabulary_languages": {"greetings": ["en", "fr"]},
    }

    assert _findings(FIXTURE, **rules) == ()
    (finding,) = _findings(content, **rules)
    assert finding.code == "protocol.vocabulary_value_language_missing"
    assert "'fr'" in finding.message and "1 entry" in finding.message
    assert finding.location.endswith("[@CVE_ID='cve-farewell']")


# Tier metadata rules ---------------------------------------------------------


@pytest.mark.parametrize(
    ("attribute", "rule_key", "code"),
    [
        (
            b'PARTICIPANT="P01" ',
            "participant_tiers",
            "protocol.tier_participant_missing",
        ),
        (b'ANNOTATOR="A02"', "annotator_tiers", "protocol.tier_annotator_missing"),
    ],
)
def test_tiers_can_require_participant_and_annotator(
    attribute: bytes, rule_key: str, code: str
) -> None:
    assert _findings(FIXTURE, required_tiers=BOTH_TIERS, **{rule_key: BOTH_TIERS}) == ()

    # The second tier in the fixture carries these exact attribute values.
    position = FIXTURE.index(b'TIER_ID="translation"')
    content = FIXTURE[:position] + FIXTURE[position:].replace(attribute, b"", 1)
    (finding,) = _findings(content, required_tiers=BOTH_TIERS, **{rule_key: BOTH_TIERS})

    assert finding.code == code
    assert finding.location.endswith("[@TIER_ID='translation']")


def test_a_blank_participant_does_not_satisfy_the_rule() -> None:
    content = _replace(
        b'PARTICIPANT="P01" ANNOTATOR="A01"', b'PARTICIPANT="  " ANNOTATOR="A01"'
    )

    (finding,) = _findings(
        content, required_tiers=["utterance"], participant_tiers=["utterance"]
    )

    assert finding.code == "protocol.tier_participant_missing"


def test_tiers_can_require_a_content_language() -> None:
    rules = {"required_tiers": BOTH_TIERS, "tier_languages": {"translation": "fr"}}
    assert _findings(FIXTURE, **rules) == ()

    content = _replace(b'DEFAULT_LOCALE="fra" LANG_REF="fr"', b'DEFAULT_LOCALE="fra"')
    (finding,) = _findings(content, **rules)

    assert finding.code == "protocol.tier_language_mismatch"
    assert "'fr'" in finding.message


# Completeness rules ----------------------------------------------------------


def test_empty_annotation_values_are_counted_on_listed_tiers() -> None:
    rules = {"required_tiers": ["utterance"], "non_empty_tiers": ["utterance"]}
    assert _findings(_second_utterance(b"Hello"), **rules) == ()

    (finding,) = _findings(_second_utterance(b"   "), **rules)

    assert finding.code == "protocol.empty_annotation_values"
    assert "1 annotation " in finding.message
    assert finding.location.endswith("[@ANNOTATION_ID='a3']")


def test_time_aligned_tiers_refuse_unaligned_and_reference_annotations() -> None:
    rules = {"required_tiers": BOTH_TIERS, "time_aligned_tiers": ["utterance"]}
    assert _findings(FIXTURE, **rules) == ()

    unaligned = _replace(
        b'<TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="2500"/>',
        b'<TIME_SLOT TIME_SLOT_ID="ts2"/>',
    )
    (finding,) = _findings(unaligned, **rules)
    assert finding.code == "protocol.unaligned_annotations"
    assert finding.location.endswith("[@ANNOTATION_ID='a1']")

    (reference,) = _findings(
        FIXTURE,
        required_tiers=BOTH_TIERS,
        time_aligned_tiers=["translation"],
    )
    assert reference.code == "protocol.unaligned_annotations"
    assert reference.location.endswith("[@ANNOTATION_ID='a2']")


# Linguistic-type constraint rules --------------------------------------------


def test_linguistic_types_can_require_a_constraint_stereotype() -> None:
    rules = {
        "linguistic_type_constraints": {
            "translation-type": "Symbolic_Association",
            "utterance-type": "none",
        }
    }
    assert _findings(FIXTURE, **rules) == ()

    findings = _findings(
        FIXTURE,
        linguistic_type_constraints={
            "translation-type": "Symbolic_Subdivision",
            "utterance-type": "Included_In",
            "gloss-type": "none",
        },
    )

    assert _codes(findings) == [
        "protocol.linguistic_type_missing",
        "protocol.linguistic_type_constraint_mismatch",
        "protocol.linguistic_type_constraint_mismatch",
    ]
    assert "no constraint" in findings[2].message


def test_unknown_stereotypes_are_refused() -> None:
    with pytest.raises(ValidationError):
        ProtocolRules.model_validate(
            {"linguistic_type_constraints": {"gloss-type": "Time_Division"}}
        )


# Consistency of the rules themselves -----------------------------------------


@pytest.mark.parametrize(
    "rules",
    [
        {"vocabulary_tiers": ["utterance"]},
        {"participant_tiers": ["utterance"]},
        {"annotator_tiers": ["utterance"]},
        {"tier_languages": {"utterance": "en"}},
        {"non_empty_tiers": ["utterance"]},
        {"time_aligned_tiers": ["utterance"]},
    ],
)
def test_tier_rules_name_required_tiers(rules: dict[str, object]) -> None:
    """A tier rule on an optional tier would pass silently when the tier is absent."""
    with pytest.raises(ValidationError, match="must also be required: utterance"):
        ProtocolRules.model_validate(rules)


def test_vocabulary_language_rules_name_required_vocabularies() -> None:
    with pytest.raises(ValidationError, match="must also be required: greetings"):
        ProtocolRules.model_validate({"vocabulary_languages": {"greetings": ["en"]}})


def test_every_new_family_accepts_a_warning_severity() -> None:
    rules = ProtocolRules(
        required_tiers=["utterance"],
        non_empty_tiers=["utterance"],
        severities={"non_empty_tiers": ValidationSeverity.WARNING},
    )

    (finding,) = evaluate_protocol_rules(validate_eaf(_second_utterance(b"")), rules)

    assert finding.severity == ValidationSeverity.WARNING
