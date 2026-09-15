"""What the validator release fingerprint covers, and what it must not."""

from pathlib import Path

import app.service.protocol as protocol_service
from app.elan.validation import SCHEMA_PATH
from app.service import protocol_evaluation
from app.service.protocol_evaluation import (
    VALIDATOR_SOURCES,
    VALIDATOR_VERSION,
    validator_checksum,
)

APP_ROOT = Path(protocol_evaluation.__file__).resolve().parents[1]


def test_the_fingerprint_covers_every_source_that_decides_an_outcome() -> None:
    assert set(VALIDATOR_SOURCES) == {
        SCHEMA_PATH,
        APP_ROOT / "elan" / "validation.py",
        APP_ROOT / "elan" / "xsd_types.py",
        APP_ROOT / "service" / "protocol_evaluation.py",
    }
    assert all(source.is_file() for source in VALIDATOR_SOURCES)


def test_protocol_administration_code_is_not_part_of_the_fingerprint() -> None:
    """Editing unrelated service code must not halt validation everywhere."""
    assert Path(protocol_service.__file__).resolve() not in VALIDATOR_SOURCES


def test_the_fingerprint_changes_when_any_covered_source_changes(
    tmp_path: Path,
) -> None:
    sources = []
    for index in range(3):
        source = tmp_path / f"source-{index}.py"
        source.write_text(f"rule {index}")
        sources.append(source)
    original = validator_checksum(sources, version="9")

    for source in sources:
        before = source.read_text()
        source.write_text(before + " # changed")
        assert validator_checksum(sources, version="9") != original, source.name
        source.write_text(before)

    assert validator_checksum(sources, version="9") == original
    assert validator_checksum(sources, version="10") != original


def test_semantic_validation_is_covered_because_it_changes_outcomes() -> None:
    """Release 1 hashed the protocol service but not the semantic validator.

    Two semantic fixes then changed outcomes under the same release. Version 2
    records them, and the semantic validator is now fingerprinted.
    """
    assert APP_ROOT / "elan" / "validation.py" in VALIDATOR_SOURCES
    assert int(VALIDATOR_VERSION) >= 2
