"""Reading an accepted revision's projection across projection versions."""

from pathlib import Path

from app.elan.projection import EAF_PROJECTION_VERSION
from app.model.project_revision import ProjectRevisionEaf
from app.service.project_revision import revision_projection

SOURCE = (
    Path(__file__).parents[1] / "fixtures" / "eaf" / "every-element.eaf"
).read_bytes()
VERSION_ONE = {
    "projection_version": "1",
    "tiers": [],
    "controlled_vocabularies": [{"tag": "CONTROLLED_VOCABULARY", "xml": "<...>"}],
}


def _entry(parser_version: str, projection: dict, raw_xml: bytes) -> ProjectRevisionEaf:
    return ProjectRevisionEaf(
        filename="session.eaf",
        sha256="0" * 64,
        raw_xml=raw_xml,
        parser_version=parser_version,
        structured_projection=projection,
    )


def test_a_current_projection_is_returned_as_stored() -> None:
    stored = {"projection_version": EAF_PROJECTION_VERSION, "marker": True}
    # The source is not valid EAF: proof it is not parsed again needlessly.
    entry = _entry(EAF_PROJECTION_VERSION, stored, b"not an eaf document")

    assert revision_projection(entry) is stored


def test_an_older_projection_is_re_derived_from_its_stored_source() -> None:
    entry = _entry("1", dict(VERSION_ONE), SOURCE)

    projection = revision_projection(entry)

    assert projection["projection_version"] == EAF_PROJECTION_VERSION
    assert projection["controlled_vocabularies"][0]["entries"][0]["cve_id"] == (
        "cve-greeting"
    )
    assert projection["lexicon_references"][0]["lex_ref_id"] == "lex-greetings"
    # The immutable row itself is left exactly as written.
    assert entry.structured_projection == VERSION_ONE
    assert entry.parser_version == "1"


def test_history_stays_readable_when_current_rules_refuse_the_source() -> None:
    entry = _entry("1", dict(VERSION_ONE), b"<ANNOTATION_DOCUMENT/>")

    assert revision_projection(entry) == VERSION_ONE
