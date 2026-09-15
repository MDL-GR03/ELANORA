"""The versioned JSON projection of an EAF revision: complete and typed."""

import json
from pathlib import Path

from lxml import etree

from app.elan.parser import parse_eaf
from app.elan.projection import EAF_PROJECTION_VERSION, document_projection

FIXTURES = Path(__file__).parents[1] / "fixtures" / "eaf"
COMPLETE = FIXTURES / "complete-valid.eaf"
EVERY_ELEMENT = FIXTURES / "every-element.eaf"


def _projection(path: Path) -> dict:
    return document_projection(parse_eaf(path.read_bytes()))


def test_nothing_in_the_document_is_left_out_of_the_projection() -> None:
    """Every attribute value and text in an EAF using every element type survives.

    The fixture contains each element type the vendored EAF 3.0 schema allows.
    """
    projection = json.dumps(_projection(EVERY_ELEMENT), ensure_ascii=False)
    root = etree.fromstring(EVERY_ELEMENT.read_bytes())

    def present(value: str) -> bool:
        # A value appears whole, or, being a space-separated IDREFS list that
        # the projection turns into a JSON list, reference by reference.
        return value in projection or all(
            f'"{token}"' in projection for token in value.split()
        )

    missing = []
    for element in root.iter():
        for name, value in element.attrib.items():
            if name.startswith("{"):
                continue  # namespace declarations such as xsi:schemaLocation
            if not present(value):
                missing.append(f"{element.tag}@{name}={value!r}")
        text = (element.text or "").strip()
        if text and text not in projection:
            missing.append(f"{element.tag} text {text!r}")

    assert missing == []


def test_the_projection_is_versioned_and_serializable() -> None:
    projection = _projection(COMPLETE)
    assert projection["projection_version"] == EAF_PROJECTION_VERSION == "2"
    json.dumps(projection)


def test_controlled_vocabularies_are_queryable_per_language() -> None:
    vocabulary = _projection(EVERY_ELEMENT)["controlled_vocabularies"][0]

    assert vocabulary["cv_id"] == "greetings"
    assert vocabulary["descriptions"] == [{"lang_ref": "en", "text": "Greeting values"}]
    entry = vocabulary["entries"][0]
    assert entry["cve_id"] == "cve-greeting"
    assert entry["external_refs"] == ["er-concept"]
    assert entry["values"] == [
        {"lang_ref": "en", "value": "Hello", "description": "An opening greeting"},
        {"lang_ref": "fr", "value": "Bonjour", "description": "Salutation initiale"},
    ]


def test_linguistic_types_expose_their_constraints_and_links() -> None:
    types = {
        item["linguistic_type_id"]: item
        for item in _projection(EVERY_ELEMENT)["linguistic_types"]
    }

    utterance = types["utterance-type"]
    assert utterance["time_alignable"] is True
    assert utterance["graphic_references"] is False
    assert utterance["controlled_vocabulary_ref"] == "greetings"
    assert utterance["lexicon_ref"] == "lex-greetings"
    assert types["translation-type"]["constraints"] == "Symbolic_Association"


def test_lexicon_references_are_projected() -> None:
    (lexicon,) = _projection(EVERY_ELEMENT)["lexicon_references"]

    assert lexicon == {
        "lex_ref_id": "lex-greetings",
        "name": "Greetings lexicon",
        "type": "LMF",
        "url": "https://example.org/lexicons/greetings",
        "lexicon_id": "greetings-v1",
        "lexicon_name": "Greetings",
        "datcat_id": "dc-1234",
        "datcat_name": "greeting",
        "attributes": {},
    }


def test_reference_link_sets_keep_both_link_kinds_and_their_targets() -> None:
    (link_set,) = _projection(EVERY_ELEMENT)["reference_link_sets"]

    assert link_set["link_set_id"] == "links-1"
    assert link_set["cv_ref"] == "greetings"
    (cross,) = link_set["cross_links"]
    assert (cross["ref1"], cross["ref2"], cross["directionality"]) == (
        "a2",
        "a1",
        "unidirectional",
    )
    assert cross["ref_type"] == "translation"
    assert cross["text"] == "Bonjour translates Hello"
    (group,) = link_set["group_links"]
    assert group["refs"] == ["a1", "a2"]


def test_reference_lists_are_lists_and_header_metadata_is_typed() -> None:
    projection = _projection(EVERY_ELEMENT)
    annotation = projection["tiers"][0]["annotations"][0]

    assert annotation["external_refs"] == ["er-concept", "er-lexicon"]
    assert annotation["language_ref"] == "en"
    header = projection["header"]
    assert header["properties"][0] == {
        "name": "URN",
        "value": "urn:nl-mpi-tools-elan-eaf:00000000-0000-4000-8000-000000000001",
        "attributes": {},
    }
    (linked,) = header["linked_files"]
    assert linked["link_url"] == "file:///notes/session-001.txt"
    assert linked["time_origin_ms"] == 0
    assert projection["licenses"] == [
        {
            "url": "https://creativecommons.org/licenses/by/4.0/",
            "text": "CC BY 4.0",
            "attributes": {},
        }
    ]
    assert projection["languages"][0]["lang_label"] == "English"
    assert projection["locales"][0]["country_code"] == "GB"
    assert projection["constraints"][0]["stereotype"] == "Symbolic_Association"
    assert projection["external_references"][0]["ext_ref_id"] == "er-lexicon"


def test_tiers_and_annotations_keep_their_structure() -> None:
    projection = _projection(COMPLETE)

    assert [tier["tier_id"] for tier in projection["tiers"]] == [
        "utterance",
        "translation",
    ]
    assert projection["tiers"][0]["annotations"][0]["kind"] == "alignable"
    assert projection["tiers"][1]["annotations"][0]["kind"] == "reference"
    assert projection["time_slots"] == {"ts1": 1000, "ts2": 2500}
