"""Per-rule severity: warnings are recorded but never block."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.elan.validation import validate_eaf
from app.model.enums import ValidationSeverity
from app.schema.protocol import ProtocolRules
from app.service.protocol_evaluation import (
    blocking_findings,
    evaluate_protocol_rules,
)

FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
).read_bytes()


def test_rules_published_before_severities_existed_are_all_errors() -> None:
    """Stored rules have no severities key; they must keep blocking as before."""
    rules = ProtocolRules.model_validate({"required_tiers": ["missing-tier"]})

    assert rules.severity_of("required_tiers") == ValidationSeverity.ERROR
    (finding,) = evaluate_protocol_rules(
        validate_eaf(FIXTURE), rules, filename="session.eaf"
    )
    assert finding.severity == ValidationSeverity.ERROR
    assert blocking_findings([finding]) == (finding,)


def test_a_rule_marked_as_warning_is_reported_but_not_blocking() -> None:
    rules = ProtocolRules(
        required_tiers=["missing-tier"],
        severities={"required_tiers": ValidationSeverity.WARNING},
    )

    (finding,) = evaluate_protocol_rules(
        validate_eaf(FIXTURE), rules, filename="session.eaf"
    )

    assert finding.severity == ValidationSeverity.WARNING
    assert finding.rule_key == "required_tiers"
    assert blocking_findings([finding]) == ()


def test_warnings_and_errors_are_separated_within_one_protocol() -> None:
    rules = ProtocolRules(
        required_tiers=["missing-tier"],
        required_controlled_vocabularies=["missing-vocabulary"],
        severities={"required_tiers": ValidationSeverity.WARNING},
    )

    findings = evaluate_protocol_rules(
        validate_eaf(FIXTURE), rules, filename="session.eaf"
    )
    blocking = blocking_findings(findings)

    assert {finding.rule_key for finding in findings} == {
        "required_tiers",
        "required_controlled_vocabularies",
    }
    assert [finding.rule_key for finding in blocking] == [
        "required_controlled_vocabularies"
    ]


def test_a_severity_for_an_unknown_rule_is_refused() -> None:
    with pytest.raises(ValidationError, match="unknown rules: not_a_rule"):
        ProtocolRules(severities={"not_a_rule": ValidationSeverity.WARNING})


def test_severities_cannot_target_the_severity_map_itself() -> None:
    assert "severities" not in ProtocolRules.rule_keys()
    with pytest.raises(ValidationError):
        ProtocolRules(severities={"severities": ValidationSeverity.WARNING})
