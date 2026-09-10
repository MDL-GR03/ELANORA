"""The manual upload bundle stays aligned with its documented expectations."""

from pathlib import Path

from app.elan import AnnotationChangeKind, compare_eaf, parse_eaf
from scripts.generate_interface_review_examples import generate

SOURCE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


def test_generated_review_bundle_contains_verified_single_and_multi_subject_cases(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review-scenarios"
    generate(SOURCE, output)
    baseline = parse_eaf((output / "00-baseline" / SOURCE.name).read_bytes())
    expected = {
        "01-additions": {"added": 3},
        "02-removals": {"removed": 1},
        "03-different-topic": {"added": 2},
        "04-mixed": {"value_changed": 1, "removed": 1, "added": 4},
        "04-mixed-corrected": {"value_changed": 1, "added": 5},
    }

    for folder, expected_kinds in expected.items():
        variant = parse_eaf((output / folder / SOURCE.name).read_bytes())
        comparison = compare_eaf(baseline, variant)
        kinds: dict[str, int] = {}
        for change in comparison.changes:
            for kind in change.kinds:
                kinds[kind.value] = kinds.get(kind.value, 0) + 1
        assert kinds == expected_kinds

    collaboration = output / "06-collaboration"
    assert {
        path.relative_to(collaboration).as_posix()
        for path in collaboration.rglob("*.eaf")
    } == {
        "00-seed/episode-22.eaf",
        "00-seed/session-12.eaf",
        "00-seed/video-11.eaf",
        "01-different-subjects/researcher-a/video-11.eaf",
        "01-different-subjects/researcher-b/session-12.eaf",
        "02-compatible-same-subject/researcher-a/video-11.eaf",
        "02-compatible-same-subject/researcher-b/video-11.eaf",
        "03-conflicting-same-subject/researcher-a/video-11.eaf",
        "03-conflicting-same-subject/researcher-b/video-11.eaf",
        "04-identical-submission/researcher-a/video-11.eaf",
        "04-identical-submission/researcher-b/video-11.eaf",
        "05-multi-file/researcher-a/session-12.eaf",
        "05-multi-file/researcher-a/video-11.eaf",
    }
    assert "Two-researcher and multi-subject workflows" in (
        output / "README.md"
    ).read_text(encoding="utf-8")


def test_generated_parallel_variants_have_expected_semantic_relationships(
    tmp_path: Path,
) -> None:
    output = tmp_path / "review-scenarios"
    generate(SOURCE, output)
    collaboration = output / "06-collaboration"
    baseline = parse_eaf((collaboration / "00-seed" / "video-11.eaf").read_bytes())

    compatible_changes = []
    for researcher in ("researcher-a", "researcher-b"):
        variant = parse_eaf(
            (
                collaboration
                / "02-compatible-same-subject"
                / researcher
                / "video-11.eaf"
            ).read_bytes()
        )
        compatible_changes.append(compare_eaf(baseline, variant).changes[0])
    assert {change.annotation_id for change in compatible_changes} == {"a1", "a2"}

    conflicting_changes = []
    for researcher in ("researcher-a", "researcher-b"):
        variant = parse_eaf(
            (
                collaboration
                / "03-conflicting-same-subject"
                / researcher
                / "video-11.eaf"
            ).read_bytes()
        )
        conflicting_changes.append(compare_eaf(baseline, variant).changes[0])
    assert {change.annotation_id for change in conflicting_changes} == {"a1"}
    assert all(
        change.kinds == (AnnotationChangeKind.VALUE_CHANGED,)
        for change in conflicting_changes
    )
