"""Representative contribution revisions used to exercise semantic review."""

from copy import deepcopy
from pathlib import Path
from xml.etree import ElementTree as ET

from app.elan import AnnotationChangeKind, compare_eaf, parse_eaf
from app.service.git_command_runner import GitCommandRunner

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


def _document() -> ET.Element:
    return ET.fromstring(FIXTURE.read_bytes())  # noqa: S314 - trusted test fixture


def _bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _add_topic_tier(root: ET.Element, tier_id: str = "topic-narrative") -> ET.Element:
    topic = ET.Element(
        "TIER",
        {
            "TIER_ID": tier_id,
            "PARTICIPANT": "P01",
            "ANNOTATOR": "A01",
            "LINGUISTIC_TYPE_REF": "utterance-type",
            "DEFAULT_LOCALE": "eng",
            "LANG_REF": "en",
        },
    )
    first_type = root.find("LINGUISTIC_TYPE")
    assert first_type is not None
    root.insert(list(root).index(first_type), topic)
    return topic


def _alignable(annotation_id: str, start: str, end: str, value: str) -> ET.Element:
    wrapper = ET.Element("ANNOTATION")
    annotation = ET.SubElement(
        wrapper,
        "ALIGNABLE_ANNOTATION",
        {
            "ANNOTATION_ID": annotation_id,
            "TIME_SLOT_REF1": start,
            "TIME_SLOT_REF2": end,
        },
    )
    ET.SubElement(annotation, "ANNOTATION_VALUE").text = value
    return wrapper


def _add_slots(root: ET.Element) -> None:
    order = root.find("TIME_ORDER")
    assert order is not None
    for slot_id, value in (("ts3", "3000"), ("ts4", "4200"), ("ts5", "5000")):
        ET.SubElement(
            order, "TIME_SLOT", {"TIME_SLOT_ID": slot_id, "TIME_VALUE": value}
        )


def test_revision_adding_several_annotations_reports_each_addition() -> None:
    root = _document()
    _add_slots(root)
    utterance = root.find("TIER[@TIER_ID='utterance']")
    assert utterance is not None
    utterance.extend(
        [
            _alignable("a3", "ts2", "ts3", "How are you?"),
            _alignable("a4", "ts4", "ts5", "See you later"),
        ]
    )

    comparison = compare_eaf(parse_eaf(FIXTURE.read_bytes()), parse_eaf(_bytes(root)))

    additions = [
        change
        for change in comparison.changes
        if change.kinds == (AnnotationChangeKind.ADDED,)
    ]
    assert [change.annotation_id for change in additions] == ["a3", "a4"]


def test_revision_removing_several_annotations_reports_each_removal() -> None:
    root = _document()
    for tier_id in ("utterance", "translation"):
        tier = root.find(f"TIER[@TIER_ID='{tier_id}']")
        assert tier is not None
        for wrapper in list(tier.findall("ANNOTATION")):
            tier.remove(wrapper)

    comparison = compare_eaf(parse_eaf(FIXTURE.read_bytes()), parse_eaf(_bytes(root)))

    removals = [
        change
        for change in comparison.changes
        if change.kinds == (AnnotationChangeKind.REMOVED,)
    ]
    assert [change.annotation_id for change in removals] == ["a1", "a2"]


def test_new_topic_for_same_subject_is_visible_as_a_distinct_tier() -> None:
    root = _document()
    topic = _add_topic_tier(root, "topic-family-history")
    topic.append(_alignable("a3", "ts1", "ts2", "Childhood memory"))

    before = parse_eaf(FIXTURE.read_bytes())
    after = parse_eaf(_bytes(root))
    comparison = compare_eaf(before, after)

    added = comparison.changes[0]
    assert added.kinds == (AnnotationChangeKind.ADDED,)
    assert added.after is not None and added.after.tier_id == "topic-family-history"
    topic_tier = next(
        tier for tier in after.tiers if tier.tier_id == added.after.tier_id
    )
    assert topic_tier.participant == "P01"


def test_combined_revision_reports_add_remove_value_timing_and_topic_move() -> None:
    root = _document()
    _add_slots(root)
    utterance = root.find("TIER[@TIER_ID='utterance']")
    translation = root.find("TIER[@TIER_ID='translation']")
    assert utterance is not None and translation is not None

    moved_wrapper = utterance.find("ANNOTATION")
    assert moved_wrapper is not None
    utterance.remove(moved_wrapper)
    moved = moved_wrapper.find("ALIGNABLE_ANNOTATION")
    assert moved is not None
    moved.attrib["TIME_SLOT_REF2"] = "ts3"
    value = moved.find("ANNOTATION_VALUE")
    assert value is not None
    value.text = "A revised account"
    topic = _add_topic_tier(root, "topic-biography")
    topic.append(deepcopy(moved_wrapper))
    topic.append(_alignable("a3", "ts4", "ts5", "A newly added event"))
    for wrapper in list(translation.findall("ANNOTATION")):
        translation.remove(wrapper)

    comparison = compare_eaf(parse_eaf(FIXTURE.read_bytes()), parse_eaf(_bytes(root)))
    changes = {change.annotation_id: set(change.kinds) for change in comparison.changes}

    assert changes["a1"] == {
        AnnotationChangeKind.VALUE_CHANGED,
        AnnotationChangeKind.TIMING_CHANGED,
        AnnotationChangeKind.TIER_CHANGED,
    }
    assert changes["a2"] == {AnnotationChangeKind.REMOVED}
    assert changes["a3"] == {AnnotationChangeKind.ADDED}


def test_parallel_edits_to_the_same_eaf_produce_a_real_git_conflict(
    tmp_path: Path,
) -> None:
    runner = GitCommandRunner(tmp_path, maintain_backup=False)

    def git(*arguments: str) -> None:
        runner.run(list(arguments), check=True)

    git("init", "--initial-branch=main")
    git("config", "user.name", "ELANORA scenario test")
    git("config", "user.email", "scenario@elanora.invalid")
    target = tmp_path / "session.eaf"
    target.write_bytes(FIXTURE.read_bytes())
    git("add", "session.eaf")
    git("commit", "-m", "accepted EAF")

    git("checkout", "-b", "researcher-contribution")
    target.write_bytes(FIXTURE.read_bytes().replace(b">Hello<", b">Researcher edit<"))
    git("commit", "-am", "researcher edits annotation")

    git("checkout", "main")
    target.write_bytes(FIXTURE.read_bytes().replace(b">Hello<", b">Admin edit<"))
    git("commit", "-am", "admin edits same annotation")

    preview = runner.preview_merge("researcher-contribution")

    assert preview.status == "needs_resolution"
    assert preview.conflicted_files == ["session.eaf"]
    assert runner.run(["branch", "--show-current"], check=True).stdout.strip() == "main"
