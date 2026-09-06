"""Semantic EAF comparison scenarios for the researcher review UI."""

from pathlib import Path

import pytest

from app.elan import AnnotationChangeKind, compare_eaf, parse_eaf
from app.service.eaf_review import (
    EafReviewUnavailableError,
    compare_repository_eaf,
)
from app.service.git_operations import GitCommandRunner

FIXTURE = Path(__file__).parents[1] / "fixtures" / "eaf" / "complete-valid.eaf"


def test_value_change_is_reported_by_annotation_and_media_interval() -> None:
    original = FIXTURE.read_bytes()
    changed = original.replace(
        b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
        b"<ANNOTATION_VALUE>Good morning</ANNOTATION_VALUE>",
    )

    comparison = compare_eaf(parse_eaf(original), parse_eaf(changed))

    assert len(comparison.changes) == 1
    change = comparison.changes[0]
    assert change.annotation_id == "a1"
    assert change.kinds == (AnnotationChangeKind.VALUE_CHANGED,)
    assert change.before is not None and change.before.value == "Hello"
    assert change.after is not None and change.after.value == "Good morning"
    assert change.focus_start_ms == 1000
    assert change.focus_end_ms == 2500


def test_reference_annotation_inherits_media_interval() -> None:
    original = FIXTURE.read_bytes()
    changed = original.replace(
        b"<ANNOTATION_VALUE>Bonjour</ANNOTATION_VALUE>",
        b"<ANNOTATION_VALUE>Salut</ANNOTATION_VALUE>",
    )

    comparison = compare_eaf(parse_eaf(original), parse_eaf(changed))

    change = comparison.changes[0]
    assert change.annotation_id == "a2"
    assert change.before is not None and change.before.tier_id == "translation"
    assert change.focus_start_ms == 1000
    assert change.focus_end_ms == 2500


def test_added_and_removed_annotations_are_distinguished() -> None:
    original = FIXTURE.read_bytes()
    without_child = original.replace(
        b"""        <ANNOTATION>
            <REF_ANNOTATION ANNOTATION_ID="a2" ANNOTATION_REF="a1">
                <ANNOTATION_VALUE>Bonjour</ANNOTATION_VALUE>
            </REF_ANNOTATION>
        </ANNOTATION>
""",
        b"",
    )

    removed = compare_eaf(parse_eaf(original), parse_eaf(without_child))
    added = compare_eaf(parse_eaf(without_child), parse_eaf(original))

    assert removed.changes[0].kinds == (AnnotationChangeKind.REMOVED,)
    assert added.changes[0].kinds == (AnnotationChangeKind.ADDED,)


def test_repository_review_compares_branches_without_changing_checkout(
    tmp_path: Path,
) -> None:
    project = tmp_path / "research-project"
    project.mkdir()

    runner = GitCommandRunner(project, maintain_backup=False)

    def git(*arguments: str) -> None:
        runner.run(list(arguments), check=True)

    git("init", "--initial-branch=master")
    git("config", "user.name", "ELANORA test")
    git("config", "user.email", "test@elanora.invalid")
    target = project / "session.eaf"
    target.write_bytes(FIXTURE.read_bytes())
    git("add", "session.eaf")
    git("commit", "-m", "accepted revision")
    git("checkout", "-b", "researcher-submission")
    target.write_bytes(
        FIXTURE.read_bytes().replace(
            b"<ANNOTATION_VALUE>Hello</ANNOTATION_VALUE>",
            b"<ANNOTATION_VALUE>Good morning</ANNOTATION_VALUE>",
        )
    )
    git("commit", "-am", "submitted revision")

    comparison = compare_repository_eaf(
        tmp_path, "research-project", "researcher-submission", "session.eaf"
    )

    assert comparison.changes[0].after is not None
    assert comparison.changes[0].after.value == "Good morning"
    branch = runner.run(["branch", "--show-current"], check=True)
    assert branch.stdout.strip() == "researcher-submission"


def test_repository_review_rejects_non_eaf_and_parent_paths(tmp_path: Path) -> None:
    for filename in ("notes.txt", "../outside.eaf"):
        with pytest.raises(EafReviewUnavailableError):
            compare_repository_eaf(tmp_path, "project", "submission", filename)
