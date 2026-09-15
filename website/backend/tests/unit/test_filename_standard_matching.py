"""The server's filename matcher, exercised without mocks.

The upload page checks names in the browser with
``website/frontend/src/utils/filenameCompliance.js`` and the server checks
them again. Every existing server test replaced the matcher with a stub, which
hid that it refused every filename: the ``regex`` module reads a ``{name}``
placeholder as its own syntax, so building the pattern failed and matching
fell back to "not compliant". These cases pin the browser's semantics.
"""

import pytest

from app.utils.validation import ValidationUtils

STANDARD = {
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


@pytest.mark.parametrize(
    ("filename", "compliant"),
    [
        ("042_AB.eaf", True),
        ("elan_042_AB.eaf", False),
        ("042_CD.eaf", True),
        ("042_XY.eaf", False),
        ("142_AB.eaf", False),
        ("42_AB.eaf", False),
        ("042_ABC.eaf", False),
        ("042_AB", True),
    ],
)
def test_filenames_are_judged_by_components(filename: str, compliant: bool) -> None:
    assert ValidationUtils.is_filename_compliant(STANDARD, filename) is compliant


def test_a_component_regex_must_match_the_whole_component() -> None:
    standard = {
        "pattern": "{session}-{rest}",
        "components": [
            {"name": "session", "regex": "[0-9]+", "accepted_values": []},
            {"name": "rest", "regex": ".+", "accepted_values": []},
        ],
    }

    assert ValidationUtils.is_filename_compliant(standard, "12-anything.eaf")
    assert not ValidationUtils.is_filename_compliant(standard, "1a-anything.eaf")


def test_only_the_last_extension_is_removed() -> None:
    standard = {
        "pattern": "{name}",
        "components": [{"name": "name", "regex": "[a-z.]+", "accepted_values": []}],
    }

    assert ValidationUtils.is_filename_compliant(standard, "session.eaf.eaf")
    assert ValidationUtils.is_filename_compliant(standard, "a.eafnotes.eaf")


def test_ranges_require_the_declared_zero_padded_width() -> None:
    standard = {
        "pattern": "{take}",
        "components": [
            {"name": "take", "regex": ".+", "accepted_values": ["01-20"]},
        ],
    }

    assert ValidationUtils.is_filename_compliant(standard, "07.eaf")
    assert not ValidationUtils.is_filename_compliant(standard, "7.eaf")
    assert not ValidationUtils.is_filename_compliant(standard, "+7.eaf")
    assert not ValidationUtils.is_filename_compliant(standard, "21.eaf")


def test_an_invalid_regex_is_not_compliant_rather_than_an_error() -> None:
    standard = {
        "pattern": "{broken}",
        "components": [{"name": "broken", "regex": "(", "accepted_values": []}],
    }

    assert not ValidationUtils.is_filename_compliant(standard, "x.eaf")
