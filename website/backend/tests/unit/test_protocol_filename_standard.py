"""Filename standards frozen into protocol snapshots."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.elan.validation import validate_eaf
from app.model.enums import ValidationSeverity
from app.schema.protocol import FilenameStandardRule, ProtocolRules
from app.service.protocol_evaluation import evaluate_protocol_rules
from app.utils.validation import ValidationUtils

FIXTURE = (
    Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
).read_bytes()
STANDARD = {
    "name": "Session and signer",
    "pattern": "{session}_{signer}",
    "components": [
        {"name": "session", "regex": r"\d{3}", "accepted_values": ["001-099"]},
        {
            "name": "signer",
            "regex": "[A-Z]{2}",
            "accepted_values": ["AB", "/^C[A-Z]$/i"],
        },
    ],
}
NAMES = [
    "042_AB.eaf",
    "elan_files/042_AB.eaf",
    "042_CD.eaf",
    "042_XY.eaf",
    "142_AB.eaf",
    "42_AB.eaf",
    "042_ABC.eaf",
]


def _findings(filename: str, **rules: object):
    return evaluate_protocol_rules(
        validate_eaf(FIXTURE),
        ProtocolRules.model_validate(rules),
        filename=filename,
    )


@pytest.mark.parametrize("filename", NAMES)
def test_a_frozen_standard_judges_names_like_the_upload_check(filename: str) -> None:
    """Copying a standard into a protocol must not change which names pass."""
    legacy = ValidationUtils.is_filename_compliant(
        STANDARD, filename.rsplit("/", 1)[-1]
    )

    findings = _findings(filename, filename_standard=STANDARD)

    assert (findings == ()) is legacy


def test_a_non_compliant_name_is_reported_with_the_standard() -> None:
    (finding,) = _findings("142_AB.eaf", filename_standard=STANDARD)

    assert finding.code == "protocol.filename_not_compliant"
    assert finding.rule_key == "filename_standard"
    assert finding.location == "filename"
    assert "'142_AB.eaf'" in finding.message
    assert "Session and signer" in finding.message


def test_components_are_read_from_their_own_placeholder() -> None:
    """Group numbers would pair components with the wrong text if reordered."""
    standard = {
        "name": "Signer first",
        "pattern": "{signer}-{session}",
        "components": [
            {"name": "session", "regex": "[0-9]+", "accepted_values": ["01-09"]},
            {"name": "signer", "regex": "[A-Z]+", "accepted_values": ["AB"]},
        ],
    }

    assert _findings("AB-07.eaf", filename_standard=standard) == ()
    assert len(_findings("AB-17.eaf", filename_standard=standard)) == 1


def test_a_filename_warning_does_not_block() -> None:
    (finding,) = _findings(
        "bad.eaf",
        filename_standard=STANDARD,
        severities={"filename_standard": "warning"},
    )

    assert finding.severity == ValidationSeverity.WARNING


def test_no_standard_accepts_any_name() -> None:
    assert _findings("anything at all.eaf") == ()


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"pattern": "{session}"}, "must appear exactly once: signer"),
        ({"pattern": "{session}_{signer}_{signer}"}, "exactly once: signer"),
        (
            {
                "components": [
                    *STANDARD["components"],
                    {"name": "session", "regex": "x", "accepted_values": []},
                ]
            },
            "component names must be unique",
        ),
        (
            {
                "components": [
                    {"name": "session", "regex": "(", "accepted_values": []},
                    STANDARD["components"][1],
                ]
            },
            "not a valid regular expression",
        ),
    ],
)
def test_unusable_standards_are_refused(change: dict, message: str) -> None:
    with pytest.raises(ValidationError, match=message):
        FilenameStandardRule.model_validate({**STANDARD, **change})
