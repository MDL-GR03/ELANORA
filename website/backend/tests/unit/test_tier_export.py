import pytest
from lxml import etree

from app.elan.validation import validate_eaf
from app.service.tier_export import (
    PROVENANCE_PROPERTY,
    ProtectedContextModifiedError,
    TierReintegrationConflictError,
    build_tier_subset,
    reintegrate_tier_subset,
    research_extract_metadata,
)

EAF = b"""<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT AUTHOR="" DATE="2026-09-06T00:00:00+00:00" FORMAT="3.0" VERSION="3.0"
 xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="http://www.mpi.nl/tools/elan/EAFv3.0.xsd">
 <HEADER MEDIA_FILE="" TIME_UNITS="milliseconds"><MEDIA_DESCRIPTOR MEDIA_URL="file:///video.mp4" MIME_TYPE="video/mp4"/></HEADER>
 <TIME_ORDER><TIME_SLOT TIME_SLOT_ID="ts1" TIME_VALUE="0"/><TIME_SLOT TIME_SLOT_ID="ts2" TIME_VALUE="100"/><TIME_SLOT TIME_SLOT_ID="ts3" TIME_VALUE="200"/><TIME_SLOT TIME_SLOT_ID="ts4" TIME_VALUE="300"/></TIME_ORDER>
 <TIER TIER_ID="parent" LINGUISTIC_TYPE_REF="align"><ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a1" TIME_SLOT_REF1="ts1" TIME_SLOT_REF2="ts2"><ANNOTATION_VALUE>p</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION></TIER>
 <TIER TIER_ID="child" PARENT_REF="parent" LINGUISTIC_TYPE_REF="ref"><ANNOTATION><REF_ANNOTATION ANNOTATION_ID="a2" ANNOTATION_REF="a1"><ANNOTATION_VALUE>c</ANNOTATION_VALUE></REF_ANNOTATION></ANNOTATION></TIER>
 <TIER TIER_ID="other" LINGUISTIC_TYPE_REF="align"><ANNOTATION><ALIGNABLE_ANNOTATION ANNOTATION_ID="a3" TIME_SLOT_REF1="ts3" TIME_SLOT_REF2="ts4"><ANNOTATION_VALUE>x</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION></ANNOTATION></TIER>
 <LINGUISTIC_TYPE LINGUISTIC_TYPE_ID="align" TIME_ALIGNABLE="true"/>
 <LINGUISTIC_TYPE LINGUISTIC_TYPE_ID="ref" TIME_ALIGNABLE="false" CONSTRAINTS="Symbolic_Association"/>
 <CONSTRAINT STEREOTYPE="Symbolic_Association" DESCRIPTION="1-1 association with a parent annotation"/>
</ANNOTATION_DOCUMENT>"""


def test_subset_keeps_parent_media_and_removes_unrelated_content():
    export = build_tier_subset(EAF, ["child"], "source.eaf")
    root = validate_eaf(export.content)

    assert [tier.get("TIER_ID") for tier in root.findall("TIER")] == ["parent", "child"]
    assert [
        slot.get("TIME_SLOT_ID") for slot in root.findall("TIME_ORDER/TIME_SLOT")
    ] == ["ts1", "ts2"]
    assert root.find("HEADER/MEDIA_DESCRIPTOR") is not None
    assert root.find(f"HEADER/PROPERTY[@NAME='{PROVENANCE_PROPERTY}']") is not None
    assert export.automatically_included_tiers == ("parent",)


def test_subset_includes_baseline_context_and_rejects_undeclared_edits():
    export = build_tier_subset(
        EAF,
        ["child"],
        "source.eaf",
        context_tier_names=["other"],
    )
    root = validate_eaf(export.content)
    metadata = research_extract_metadata(export.content)

    assert [tier.get("TIER_ID") for tier in root.findall("TIER")] == [
        "parent",
        "child",
        "other",
    ]
    assert metadata is not None
    assert metadata["context_tiers"] == ["other"]

    edited = _replace_value(export.content, "other", "undeclared context edit")
    with pytest.raises(ProtectedContextModifiedError) as caught:
        reintegrate_tier_subset(EAF, edited)
    assert caught.value.tiers == ["other"]


def test_declared_baseline_correction_is_reintegrated():
    export = build_tier_subset(
        EAF,
        ["parent", "other"],
        "source.eaf",
        context_tier_names=["other"],
        editable_baseline_tier_names=["other"],
    )
    edited = _replace_value(export.content, "parent", "accepted research edit")
    edited = _replace_value(edited, "other", "accepted baseline correction")

    merged = validate_eaf(reintegrate_tier_subset(EAF, edited))

    assert merged.find("TIER[@TIER_ID='parent']//ANNOTATION_VALUE").text == (
        "accepted research edit"
    )
    assert merged.find("TIER[@TIER_ID='other']//ANNOTATION_VALUE").text == (
        "accepted baseline correction"
    )


def test_subset_rejects_unknown_tier():
    try:
        build_tier_subset(EAF, ["missing"], "source.eaf")
    except ValueError as exc:
        assert "Unknown tier" in str(exc)
    else:
        raise AssertionError("Unknown tiers must be rejected")


def _replace_value(content: bytes, tier_id: str, value: str) -> bytes:
    root = validate_eaf(content)
    tier = root.find(f"TIER[@TIER_ID='{tier_id}']")
    assert tier is not None
    annotation_value = tier.find(".//ANNOTATION_VALUE")
    assert annotation_value is not None
    annotation_value.text = value
    return etree.tostring(root.getroottree(), encoding="UTF-8", xml_declaration=True)


def test_reintegration_combines_changes_to_different_tiers():
    extract = build_tier_subset(EAF, ["child"], "source.eaf")
    edited_extract = _replace_value(extract.content, "child", "research edit")
    current = _replace_value(EAF, "other", "someone else's edit")

    merged = validate_eaf(reintegrate_tier_subset(current, edited_extract))

    assert (
        merged.find("TIER[@TIER_ID='child']//ANNOTATION_VALUE").text == "research edit"
    )
    assert (
        merged.find("TIER[@TIER_ID='other']//ANNOTATION_VALUE").text
        == "someone else's edit"
    )
    assert merged.find("TIER[@TIER_ID='parent']//ANNOTATION_VALUE").text == "p"
    assert merged.find(f"HEADER/PROPERTY[@NAME='{PROVENANCE_PROPERTY}']") is None


def test_unchanged_extract_is_an_exact_no_op():
    extract = build_tier_subset(EAF, ["child"], "source.eaf")

    assert reintegrate_tier_subset(EAF, extract.content) == EAF


def test_extract_records_curated_topic_identity_for_return_upload():
    extract = build_tier_subset(
        EAF,
        ["child"],
        "source.eaf",
        topic_name="Prosody",
        topic_id=42,
    )

    metadata = research_extract_metadata(extract.content)
    assert metadata is not None
    assert metadata["research_topic"] == "Prosody"
    assert metadata["research_topic_id"] == 42


def test_reintegration_stops_when_same_tier_changed_concurrently():
    extract = build_tier_subset(EAF, ["child"], "source.eaf")
    edited_extract = _replace_value(extract.content, "child", "research edit")
    current = _replace_value(EAF, "child", "accepted concurrent edit")

    try:
        reintegrate_tier_subset(current, edited_extract)
    except TierReintegrationConflictError as exc:
        assert exc.filename == "source.eaf"
        assert exc.tiers == ["child"]
    else:
        raise AssertionError("Concurrent edits to the same tier must stop")


def test_reintegration_does_not_move_unselected_tier_using_shared_time_slot():
    shared_root = validate_eaf(EAF)
    other = shared_root.find("TIER[@TIER_ID='other']/ANNOTATION/ALIGNABLE_ANNOTATION")
    assert other is not None
    other.set("TIME_SLOT_REF1", "ts1")
    other.set("TIME_SLOT_REF2", "ts2")
    shared = etree.tostring(shared_root.getroottree(), encoding="UTF-8")
    extract = build_tier_subset(shared, ["parent"], "source.eaf")
    extract_root = validate_eaf(extract.content)
    extract_slot = extract_root.find("TIME_ORDER/TIME_SLOT[@TIME_SLOT_ID='ts1']")
    assert extract_slot is not None
    extract_slot.set("TIME_VALUE", "25")
    edited = etree.tostring(extract_root.getroottree(), encoding="UTF-8")

    merged = validate_eaf(reintegrate_tier_subset(shared, edited))
    parent_annotation = merged.find(
        "TIER[@TIER_ID='parent']/ANNOTATION/ALIGNABLE_ANNOTATION"
    )
    other_annotation = merged.find(
        "TIER[@TIER_ID='other']/ANNOTATION/ALIGNABLE_ANNOTATION"
    )
    assert parent_annotation is not None
    assert other_annotation is not None
    assert parent_annotation.get("TIME_SLOT_REF1") != "ts1"
    assert other_annotation.get("TIME_SLOT_REF1") == "ts1"
    assert (
        merged.find("TIME_ORDER/TIME_SLOT[@TIME_SLOT_ID='ts1']").get("TIME_VALUE")
        == "0"
    )


def _add_tier(content: bytes, tier_name: str) -> bytes:
    root = validate_eaf(content)
    time_order = root.find("TIME_ORDER")
    assert time_order is not None
    time_order.append(
        etree.Element("TIME_SLOT", TIME_SLOT_ID="ts_new_1", TIME_VALUE="40")
    )
    time_order.append(
        etree.Element("TIME_SLOT", TIME_SLOT_ID="ts_new_2", TIME_VALUE="80")
    )
    tier = etree.Element("TIER", TIER_ID=tier_name, LINGUISTIC_TYPE_REF="align")
    annotation = etree.SubElement(tier, "ANNOTATION")
    alignable = etree.SubElement(
        annotation,
        "ALIGNABLE_ANNOTATION",
        ANNOTATION_ID="a_new",
        TIME_SLOT_REF1="ts_new_1",
        TIME_SLOT_REF2="ts_new_2",
    )
    etree.SubElement(alignable, "ANNOTATION_VALUE").text = "new analysis"
    root.insert(root.index(root.find("LINGUISTIC_TYPE")), tier)
    return etree.tostring(root.getroottree(), encoding="UTF-8")


def test_reintegration_adds_only_new_tiers_allowed_by_topic():
    extract = build_tier_subset(
        EAF,
        ["parent"],
        "source.eaf",
        topic_name="Prosody",
        allowed_new_tier_names=["prosody_notes"],
    )
    merged = validate_eaf(
        reintegrate_tier_subset(EAF, _add_tier(extract.content, "prosody_notes"))
    )

    assert (
        merged.find("TIER[@TIER_ID='prosody_notes']//ANNOTATION_VALUE").text
        == "new analysis"
    )
    assert merged.find("TIER[@TIER_ID='other']") is not None


def test_reintegration_rejects_new_tier_outside_topic():
    extract = build_tier_subset(
        EAF,
        ["parent"],
        "source.eaf",
        allowed_new_tier_names=["prosody_notes"],
    )

    try:
        reintegrate_tier_subset(EAF, _add_tier(extract.content, "unplanned"))
    except ValueError as exc:
        assert "outside its topic" in str(exc)
    else:
        raise AssertionError("New tiers outside the declared topic must be rejected")
