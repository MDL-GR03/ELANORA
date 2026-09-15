"""Realistic tests for the typed, lossless EAF boundary."""

import hashlib
from pathlib import Path

import pytest

from app.elan import (
    AlignableAnnotation,
    EafValidationError,
    ReferenceAnnotation,
    parse_eaf,
    parse_eaf_path,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"
CORPUS_ROOT = Path(__file__).parents[3] / "static"


def test_complete_eaf_runs_official_and_semantic_validation() -> None:
    """Parse a representative EAF without losing source or interpreted metadata."""
    content = FIXTURE.read_bytes()

    document = parse_eaf(content)

    assert document.raw_xml == content
    assert document.sha256 == hashlib.sha256(content).hexdigest()
    assert document.format_version == "3.0"
    assert document.header.time_units == "milliseconds"
    assert (
        document.header.media_descriptors[0].relative_media_url == "./session-001.mp4"
    )
    assert (
        document.header.linked_file_descriptors[0].link_url
        == "file:///notes/session-001.txt"
    )
    assert len(document.header.properties) == 2
    assert len(document.linguistic_types) == 2
    assert len(document.languages) == 2
    assert len(document.controlled_vocabularies) == 1
    assert len(document.external_references) == 1
    assert len(document.licenses) == 1

    parent, child = document.tiers
    assert parent.tier_id == "utterance"
    assert child.parent_ref == parent.tier_id
    alignable = parent.annotations[0]
    reference = child.annotations[0]
    assert isinstance(alignable, AlignableAnnotation)
    assert alignable.start_ms == 1000
    assert alignable.end_ms == 2500
    assert alignable.cv_entry_ref == "cve-greeting"
    assert isinstance(reference, ReferenceAnnotation)
    assert reference.annotation_ref == alignable.annotation_id
    assert reference.value == "Bonjour"


@pytest.mark.parametrize(
    ("literal", "expected"),
    [("true", True), ("1", True), ("false", False), ("0", False)],
)
def test_schema_booleans_accept_every_lexical_form(
    literal: str, expected: bool
) -> None:
    """xsd:boolean admits 1 and 0, so reading only "true" would invert them."""
    content = FIXTURE.read_bytes().replace(
        b'TIME_ALIGNABLE="true"\n        GRAPHIC_REFERENCES="false"',
        f'TIME_ALIGNABLE="true"\n        GRAPHIC_REFERENCES="{literal}"'.encode(),
        1,
    )

    document = parse_eaf(content)

    types = {item.linguistic_type_id: item for item in document.linguistic_types}
    assert types["utterance-type"].graphic_references is expected


def test_a_type_declared_time_alignable_with_1_accepts_aligned_annotations() -> None:
    """The validator read TIME_ALIGNABLE="1" as false and refused the valid file."""
    content = FIXTURE.read_bytes().replace(
        b'LINGUISTIC_TYPE_ID="utterance-type" TIME_ALIGNABLE="true"',
        b'LINGUISTIC_TYPE_ID="utterance-type" TIME_ALIGNABLE="1"',
        1,
    )

    document = parse_eaf(content)

    types = {item.linguistic_type_id: item for item in document.linguistic_types}
    assert types["utterance-type"].time_alignable is True


def test_parse_path_records_reproducibility_metadata() -> None:
    """A path import records an absolute source path, size, and modification time."""
    document = parse_eaf_path(FIXTURE)

    assert document.source_path == FIXTURE.resolve()
    assert document.source_size == FIXTURE.stat().st_size
    assert document.source_modified_at is not None


@pytest.mark.parametrize(
    ("old", "new", "expected_code"),
    [
        (b'ANNOTATION_REF="a1"', b'ANNOTATION_REF="missing"', "unknown_annotation_ref"),
        (b'TIME_SLOT_REF2="ts2"', b'TIME_SLOT_REF2="missing"', "unknown_time_slot"),
        (b'CVE_REF="cve-greeting"', b'CVE_REF="missing"', "unknown_cv_entry"),
        (b'PARENT_REF="utterance"', b'PARENT_REF="missing"', "unknown_parent_tier"),
    ],
)
def test_cross_reference_corruption_is_rejected(
    old: bytes, new: bytes, expected_code: str
) -> None:
    """Reject dangling references that a shallow XML check would accept."""
    content = FIXTURE.read_bytes().replace(old, new, 1)

    with pytest.raises(EafValidationError) as error:
        parse_eaf(content)

    assert expected_code in {issue.code for issue in error.value.issues}


def test_an_annotation_may_cite_several_external_references() -> None:
    """EAF 3.0 declares an annotation's EXT_REF as IDREFS, a list of references.

    The semantic check compared the whole list against known identifiers, so a
    schema-valid file citing two references was refused at upload.
    """
    content = FIXTURE.read_bytes().replace(
        b'EXT_REF="er-concept">',
        b'EXT_REF="er-concept er-lexicon">',
        1,
    )
    content = content.replace(
        b"    <EXTERNAL_REF ",
        b'    <EXTERNAL_REF EXT_REF_ID="er-lexicon" TYPE="lexen_id" VALUE="lex#1"/>\n'
        b"    <EXTERNAL_REF ",
        1,
    )

    document = parse_eaf(content)

    assert document.tiers[0].annotations[0].ext_ref == "er-concept er-lexicon"


def test_each_cited_external_reference_must_exist() -> None:
    """Splitting the list must not let an unknown reference slip through."""
    content = FIXTURE.read_bytes().replace(
        b'EXT_REF="er-concept">',
        b'EXT_REF="er-concept er-missing">',
        1,
    )

    with pytest.raises(EafValidationError) as error:
        parse_eaf(content)

    issues = [i for i in error.value.issues if i.code == "unknown_external_ref"]
    assert len(issues) == 1
    assert "er-missing" in issues[0].message
    assert "er-concept" not in issues[0].message.replace("er-missing", "")


def test_overlapping_annotations_on_one_tier_are_rejected() -> None:
    """Reject an overlap that remains schema-valid but is not a valid ELAN tier."""
    content = FIXTURE.read_bytes().replace(
        b'<TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="2500"/>',
        b'<TIME_SLOT TIME_SLOT_ID="ts3" TIME_VALUE="2000"/>'
        b'<TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="2500"/>'
        b'<TIME_SLOT TIME_SLOT_ID="ts4" TIME_VALUE="3000"/>',
        1,
    )
    content = content.replace(
        b"        </ANNOTATION>\n    </TIER>",
        b"        </ANNOTATION>\n"
        b'        <ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a-overlap" '
        b'TIME_SLOT_REF1="ts3" TIME_SLOT_REF2="ts4">'
        b"<ANNOTATION_VALUE>Overlap</ANNOTATION_VALUE>"
        b"</ALIGNABLE_ANNOTATION></ANNOTATION>\n    </TIER>",
        1,
    )

    with pytest.raises(EafValidationError) as error:
        parse_eaf(content)

    assert "overlapping_annotations" in {issue.code for issue in error.value.issues}


def test_empty_annotation_value_is_preserved() -> None:
    """Empty annotation values are valid EAF data and must not disappear."""
    content = FIXTURE.read_bytes().replace(
        b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
        b"<ANNOTATION_VALUE></ANNOTATION_VALUE>",
    )

    document = parse_eaf(content)

    assert document.tiers[0].annotations[0].value == ""


def test_real_repository_corpus_exercises_large_files() -> None:
    """Validate and parse every real corpus file shipped with ELANORA."""
    candidates = sorted(CORPUS_ROOT.rglob("*.eaf"))
    documents = [parse_eaf_path(path) for path in candidates]

    assert len(documents) == 12
    assert sum(len(document.annotations) for document in documents) > 20_000
    assert all(document.raw_xml for document in documents)
