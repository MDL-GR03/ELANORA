"""Generate manual EAF review scenarios from an accepted project document."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from xml.etree import ElementTree as ET


def load(path: Path) -> ET.Element:
    return ET.fromstring(path.read_bytes())  # noqa: S314 - trusted local EAF


def save(root: ET.Element, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ET.indent(root, space="    ")
    path.write_bytes(ET.tostring(root, encoding="utf-8", xml_declaration=True))


def copy(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def annotations(root: ET.Element) -> list[tuple[ET.Element, ET.Element, ET.Element]]:
    result = []
    for tier in root.findall("TIER"):
        for wrapper in tier.findall("ANNOTATION"):
            node = next(iter(wrapper), None)
            if node is not None:
                result.append((tier, wrapper, node))
    return result


def next_ids(root: ET.Element) -> tuple[int, int, int]:
    annotation_numbers = [
        int(value[1:])
        for _, _, node in annotations(root)
        if (value := node.get("ANNOTATION_ID", ""))[1:].isdigit()
    ]
    slot_numbers = [
        int(value[2:])
        for slot in root.findall("./TIME_ORDER/TIME_SLOT")
        if (value := slot.get("TIME_SLOT_ID", ""))[2:].isdigit()
    ]
    time_values = [
        int(value)
        for slot in root.findall("./TIME_ORDER/TIME_SLOT")
        if (value := slot.get("TIME_VALUE")) and value.isdigit()
    ]
    return (
        max(annotation_numbers, default=0) + 1,
        max(slot_numbers, default=0) + 1,
        max(time_values, default=0),
    )


def add_annotations(root: ET.Element, count: int = 3) -> list[str]:
    target = next(
        tier
        for tier in root.findall("TIER")
        if tier.find(".//ALIGNABLE_ANNOTATION") is not None
    )
    order = root.find("TIME_ORDER")
    if order is None:
        raise ValueError("Source EAF has no TIME_ORDER")
    annotation_id, slot_id, last_time = next_ids(root)
    added_ids = []
    for offset in range(count):
        start_id = f"ts{slot_id + offset * 2}"
        end_id = f"ts{slot_id + offset * 2 + 1}"
        start = last_time + 1000 + offset * 2000
        ET.SubElement(order, "TIME_SLOT", TIME_SLOT_ID=start_id, TIME_VALUE=str(start))
        ET.SubElement(
            order, "TIME_SLOT", TIME_SLOT_ID=end_id, TIME_VALUE=str(start + 1200)
        )
        wrapper = ET.SubElement(target, "ANNOTATION")
        node = ET.SubElement(
            wrapper,
            "ALIGNABLE_ANNOTATION",
            ANNOTATION_ID=f"a{annotation_id + offset}",
            TIME_SLOT_REF1=start_id,
            TIME_SLOT_REF2=end_id,
        )
        added_ids.append(node.attrib["ANNOTATION_ID"])
        ET.SubElement(
            node, "ANNOTATION_VALUE"
        ).text = f"Manual test addition {offset + 1}"
    return added_ids


def remove_annotations(root: ET.Element, count: int = 3) -> None:
    referenced = {
        node.get("ANNOTATION_REF")
        for _, _, node in annotations(root)
        if node.get("ANNOTATION_REF")
    }
    removable = [
        item
        for item in annotations(root)
        if item[2].get("ANNOTATION_ID") not in referenced
    ][-count:]
    for tier, wrapper, _ in removable:
        tier.remove(wrapper)


def remove_annotation(root: ET.Element, annotation_id: str) -> None:
    for tier, wrapper, node in annotations(root):
        if node.get("ANNOTATION_ID") == annotation_id:
            tier.remove(wrapper)
            return
    raise ValueError(f"Source EAF has no annotation {annotation_id}")


def add_topic(root: ET.Element, label: str = "topic-new-research-question") -> None:
    source = next(
        tier
        for tier in root.findall("TIER")
        if tier.find(".//ALIGNABLE_ANNOTATION") is not None
    )
    annotation_id, slot_id, last_time = next_ids(root)
    order = root.find("TIME_ORDER")
    if order is None:
        raise ValueError("Source EAF has no TIME_ORDER")
    topic = ET.Element(
        "TIER",
        TIER_ID=label,
        PARTICIPANT=source.get("PARTICIPANT", "P01"),
        ANNOTATOR=source.get("ANNOTATOR", "interface-test"),
        LINGUISTIC_TYPE_REF=source.get("LINGUISTIC_TYPE_REF", "default-lt"),
    )
    for offset, value in enumerate(
        ("New topic observation", "Same subject, different research topic")
    ):
        start_id = f"ts{slot_id + offset * 2}"
        end_id = f"ts{slot_id + offset * 2 + 1}"
        start = last_time + 1000 + offset * 2000
        ET.SubElement(order, "TIME_SLOT", TIME_SLOT_ID=start_id, TIME_VALUE=str(start))
        ET.SubElement(
            order, "TIME_SLOT", TIME_SLOT_ID=end_id, TIME_VALUE=str(start + 1200)
        )
        wrapper = ET.SubElement(topic, "ANNOTATION")
        node = ET.SubElement(
            wrapper,
            "ALIGNABLE_ANNOTATION",
            ANNOTATION_ID=f"a{annotation_id + offset}",
            TIME_SLOT_REF1=start_id,
            TIME_SLOT_REF2=end_id,
        )
        ET.SubElement(node, "ANNOTATION_VALUE").text = value
    first_type = root.find("LINGUISTIC_TYPE")
    root.insert(
        list(root).index(first_type) if first_type is not None else len(root), topic
    )


def change_first_value(root: ET.Element, value: str) -> None:
    first = annotations(root)[0][2].find("ANNOTATION_VALUE")
    if first is None:
        raise ValueError("Source EAF has no annotation value")
    first.text = value


def change_annotation_at(root: ET.Element, index: int, replacement: str) -> None:
    available = [
        value
        for _, _, node in annotations(root)
        if (value := node.find("ANNOTATION_VALUE")) is not None
    ]
    if index >= len(available):
        raise ValueError(f"Source EAF has fewer than {index + 1} annotations")
    available[index].text = replacement


def write_readme(output: Path, filename: str, second_cycle_annotation_id: str) -> None:
    text = f"""# ELANORA interface review examples

This walkthrough uses two simultaneous browser sessions and the `test` project. All variants intentionally keep the filename `{filename}` so ELANORA recognizes them as revisions of `elan_files/{filename}`.

The clean test state is **not an empty project**. It starts with
`elan_files/{filename}` already accepted and identical to `00-baseline/{filename}`.
"Clean" means there are no pending contributions or active review cases. This
accepted file is required for modified-file comparisons.

## 1. Prepare the two sessions

1. Open ELANORA at `http://localhost:8777` in your normal browser window.
2. Log in as `MDL`. This is the reviewer window.
3. Open a private/incognito window at the same address.
4. Log in with username `external.researcher` and password `Elanora-Test-2026!`. This is the contributor window.
5. Select the `test` project in both windows.
6. In the MDL window, open **Contributions → Incoming work** and ensure automatic acceptance is disabled.

When choosing a test file, select the individual `.eaf` file. Do not upload its containing scenario folder.

## 2. Test added annotations

1. In the researcher window, open **File Upload**.
2. Select `01-additions/{filename}` and upload it to `test`.
3. In the MDL window, open **Contributions → Incoming work** and refresh.
4. Open **View Details** on the new contribution.
5. Under **ELAN annotation changes**, expand `{filename}` with **Review changes**.

Expected result:

- The contribution contains one modified EAF file.
- Upload type says **Modified files**, not **New files only**.
- The semantic preview reports exactly **3 changes**.
- All three changes are labelled **added**.
- Each change has no accepted value on the left and a submitted annotation on the right.

Leave this contribution pending while testing the other normal scenarios. Do not accept it, because acceptance changes the baseline.

## 3. Test removed annotations

1. In the researcher window, upload `02-removals/{filename}`.
2. Refresh Incoming work as MDL.
3. Open **View Details**, then expand the EAF under **ELAN annotation changes**.

Expected result:

- The semantic preview reports exactly **3 changes**.
- All three are labelled **removed**.
- Each change shows an accepted annotation on the left and “Annotation removed” on the right.

## 4. Test another research topic for the same participant

1. As the researcher, upload `03-different-topic/{filename}`.
2. Refresh and inspect the new contribution as MDL.

Expected result:

- The preview reports exactly **2 added annotations**.
- Both additions belong to tier `topic-new-research-question`.
- The tier uses the same participant as the source EAF.
- The two earlier pending contributions remain separate; this is not a correction version until it is explicitly linked to a review case.

## 5. Test the mixed scenario and correction loop

1. As the researcher, upload `04-mixed/{filename}`.
2. As MDL, refresh Incoming work and choose **View Details** on the newest contribution.
3. Expand its EAF under **ELAN annotation changes**.

Expected initial result:

- The preview reports exactly **8 affected annotations**.
- It contains **5 additions**, **2 removals**, and **1 changed value**.
- Two additions belong to the new `topic-combined-test` tier.

Now request a correction:

4. Close the preview and choose **Request correction**.
5. Enter a title such as `Review mixed EAF changes`.
6. Under **Files that must be changed**, select `elan_files/{filename}`.
7. Enter an instruction such as `Keep the new topic, restore the removed annotations, and revise the changed annotation value.`
8. Send the correction request.
9. In the researcher window, open **Contributions → Questions and corrections**.

Expected result for the researcher:

- The case says **Changes requested**.
- `{filename}` appears under **Files marked for correction**.
- The exact instruction is visible.
- The task is labelled **Needs change**.
- The researcher sees **Upload corrected files**, but not reviewer-only acceptance controls.

Submit the corrected version:

10. Click **Upload corrected files**. Uploading the requested file is the
    commit-like signal that the edit is ready for review; no separate
    "mark done" step is required.
11. Upload `04-mixed-corrected/{filename}`. This is a unique corrected revision;
    do not reuse one of the earlier pending scenario files.

Expected result:

- ELANORA asks only for the requested file, not the whole project.
- The upload is linked automatically to the existing case.
- The review state becomes **Resubmitted**. Reviewers see **Requested edits to
  review** and **Awaiting reviewer decision**; the researcher sees **Corrected
  version submitted**.
- Incoming work shows one contribution thread with version history, not two independent mergeable cards.

As MDL, test the approval branch first:

12. Expand **Review annotation changes** and verify the corrected semantic diff.
13. Choose **Approve edit and complete review**.
14. Return to Incoming work and accept the current contribution version to
    finish the merge.

Expected result:

- The review closes, while its discussion and version history remain available.
- The superseded upload cannot be accepted separately.
- Only the latest contribution version remains actionable.

To test another correction cycle, use a later fresh mixed contribution. Choose
**Request another correction** for the affected edit. The button becomes
**Cancel correction request**, and the draft panel confirms that nothing has
been sent yet. Choose **Add feedback and continue**, enter mandatory feedback,
then choose **Send revision request** and confirm it. The same case returns to
**Waiting for corrected files**, preserving the previous discussion and versions.

The dedicated files under **04-second-correction-cycle** make that test
semantically real. Upload **01-incomplete/{filename}** first. It retains the
current project values but deliberately leaves annotation `{second_cycle_annotation_id}` missing. The
reviewer can therefore request another correction with the feedback
`Annotation {second_cycle_annotation_id} is still missing.` Upload **02-final/{filename}** for the
second revision; it restores the missing annotation and matches the intended
corrected project file.

## 6. Produce a real Git conflict

A conflict is created by history, not by a special malformed file. Both the administrator and researcher must independently edit the same accepted annotation.

1. Confirm that the accepted project still uses the original baseline. `00-baseline/{filename}` and `05-conflict/baseline/{filename}` are reference copies.
2. As the researcher, upload `05-conflict/researcher/{filename}`.
3. Leave that researcher contribution pending.
4. As MDL, upload `05-conflict/admin/{filename}` as a separate contribution.
5. In Incoming work, accept the **MDL/admin** contribution first.
6. Refresh Incoming work and inspect the still-pending researcher contribution.

Expected result:

- The researcher contribution changes from ready to **Needs resolution**.
- The conflicted-files list contains `elan_files/{filename}`.
- Normal acceptance is unavailable; **Resolve conflicts** is shown instead.
- The semantic comparison shows the administrator's accepted value on the left and `Researcher version of the disputed annotation` on the right.

## 7. Resetting or repeating

The normal examples all assume `00-baseline/{filename}` is the accepted project version. Once you accept one of the semantic scenarios, later counts may differ because the baseline changed. For exact repeatable results, use a fresh project copy initialized with `00-baseline/{filename}`, or regenerate/reset the development test data before repeating the walkthrough.
"""  # noqa: S608 - documentation, not a query
    text += """

## 8. Two-researcher and multi-subject workflows

The folders under **06-collaboration** model subjects as project-relative EAF
filenames. **video-11.eaf**, **session-12.eaf**, and **episode-22.eaf** are
three distinct subjects. A topic remains a tier inside one of those files.

Use two researcher accounts with write access. The existing
**external.researcher** can be Researcher A; create or invite a second write
member as Researcher B. Keep MDL in the reviewer window.

### Seed the accepted subjects

1. Upload all three files from **06-collaboration/00-seed** together.
2. Accept that contribution as MDL.
3. Confirm Incoming work is empty.

Expected:

- The accepted project contains three new subjects.
- Each EAF is independently addressable by filename.

### Parallel work on different subjects

1. A uploads **01-different-subjects/researcher-a/video-11.eaf**.
2. B uploads **01-different-subjects/researcher-b/session-12.eaf**.
3. Confirm both contributions initially say **Ready to accept**.
4. Accept A, refresh, then accept B.

Expected:

- Accepting A does not invalidate B.
- Both contributions merge because they modify different subject files.
- The final project contains both researchers' values.

Restore video-11.eaf and session-12.eaf from **00-seed** before the next exact
scenario.

### Compatible parallel edits to the same subject

1. A uploads **02-compatible-same-subject/researcher-a/video-11.eaf**.
2. B uploads **02-compatible-same-subject/researcher-b/video-11.eaf**.
3. Accept A first and refresh B.

Expected:

- A changes the first annotation and B changes a separate second annotation.
- B remains mergeable when Git combines the independent XML regions.
- The accepted file ultimately contains both changes.

This intentionally tests Git as well as semantic compatibility. A real ELAN
save may rewrite broad XML regions and cause a textual conflict even when the
annotation edits are semantically independent.

Restore video-11.eaf from **00-seed** before continuing.

### Conflicting edits to the same subject and annotation

1. A uploads **03-conflicting-same-subject/researcher-a/video-11.eaf**.
2. B uploads **03-conflicting-same-subject/researcher-b/video-11.eaf**.
3. Accept B first and refresh A.

Expected:

- A changes to **Needs resolution**.
- **elan_files/video-11.eaf** is listed as conflicted.
- The comparison shows B's accepted interpretation against A's submission.
- A cannot use ordinary acceptance.

Restore video-11.eaf from **00-seed** before continuing.

### Identical submissions

1. A uploads **04-identical-submission/researcher-a/video-11.eaf**.
2. B uploads **04-identical-submission/researcher-b/video-11.eaf**.
3. Refresh Incoming work.

Expected:

- The older upload is the canonical pending contribution.
- The later identical tree is marked as a duplicate.
- Dismissing it does not discard unique work.

### Multi-file contribution and partial correction

1. A uploads both files from **05-multi-file/researcher-a** together.
2. MDL requests a correction only for **session-12.eaf**.
3. A follows **Upload corrected files** and uploads only the seed
   **session-12.eaf**.

Expected:

- The original contribution contains two modified subjects.
- Only session-12.eaf appears as required correction work.
- The correction upload requires only that requested file.
- Version history remains one contribution thread.
- The unrelated video-11.eaf change remains part of the contribution.

## 9. Automated verification

Run from the repository root:

    make test-db-up
    cd website/backend
    ENVIRONMENT=test \
    TEST_DATABASE_URL=postgresql+asyncpg://elanora_test:elanora-test-only@127.0.0.1:5418/elanora_test \
    poetry run pytest \
      tests/integration/test_contribution_git_workflows.py \
      tests/integration/test_review_workflow.py
    cd ../..
    make test-db-down

The automated tests use disposable PostgreSQL and temporary real Git
repositories. They verify clean two-researcher merges on different subjects,
duplicate detection, same-subject conflicts, correction ownership, version
superseding, merge blocking during review, notifications, read receipts,
rejection, archival state, and stale-write protection. They do not drive the
browser UI; the steps above remain the visual acceptance test.
"""
    (output / "README.md").write_text(text, encoding="utf-8")


def generate(source: Path, output: Path) -> None:
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    filename = source.name
    copy(source, output / "00-baseline" / filename)

    additions = load(source)
    add_annotations(additions)
    save(additions, output / "01-additions" / filename)

    removals = load(source)
    remove_annotations(removals)
    save(removals, output / "02-removals" / filename)

    topic = load(source)
    add_topic(topic)
    save(topic, output / "03-different-topic" / filename)

    mixed = load(source)
    add_annotations(mixed)
    remove_annotations(mixed, 2)
    add_topic(mixed, "topic-combined-test")
    change_first_value(mixed, "Combined scenario changed by researcher")
    save(mixed, output / "04-mixed" / filename)

    mixed_corrected = load(source)
    corrected_annotation_ids = add_annotations(mixed_corrected)
    add_topic(mixed_corrected, "topic-combined-test")
    change_first_value(mixed_corrected, "Corrected mixed-scenario annotation value")
    save(mixed_corrected, output / "04-mixed-corrected" / filename)

    second_cycle_incomplete = load(output / "04-mixed-corrected" / filename)
    second_cycle_annotation_id = corrected_annotation_ids[-1]
    remove_annotation(second_cycle_incomplete, second_cycle_annotation_id)
    save(
        second_cycle_incomplete,
        output / "04-second-correction-cycle" / "01-incomplete" / filename,
    )
    copy(
        output / "04-mixed-corrected" / filename,
        output / "04-second-correction-cycle" / "02-final" / filename,
    )

    copy(source, output / "05-conflict" / "baseline" / filename)
    researcher = load(source)
    change_first_value(researcher, "Researcher version of the disputed annotation")
    save(researcher, output / "05-conflict" / "researcher" / filename)
    admin = load(source)
    change_first_value(admin, "Administrator version of the disputed annotation")
    save(admin, output / "05-conflict" / "admin" / filename)

    collaboration = output / "06-collaboration"
    for subject_name in ("video-11.eaf", "session-12.eaf", "episode-22.eaf"):
        copy(source, collaboration / "00-seed" / subject_name)

    scenarios = (
        (
            "01-different-subjects/researcher-a/video-11.eaf",
            0,
            "Researcher A video 11 interpretation",
        ),
        (
            "01-different-subjects/researcher-b/session-12.eaf",
            1,
            "Researcher B session 12 interpretation",
        ),
        (
            "02-compatible-same-subject/researcher-a/video-11.eaf",
            0,
            "Researcher A independent annotation",
        ),
        (
            "02-compatible-same-subject/researcher-b/video-11.eaf",
            1,
            "Researcher B independent annotation",
        ),
        (
            "03-conflicting-same-subject/researcher-a/video-11.eaf",
            0,
            "Researcher A disputed interpretation",
        ),
        (
            "03-conflicting-same-subject/researcher-b/video-11.eaf",
            0,
            "Researcher B disputed interpretation",
        ),
        (
            "04-identical-submission/researcher-a/video-11.eaf",
            0,
            "Shared researcher interpretation",
        ),
        (
            "04-identical-submission/researcher-b/video-11.eaf",
            0,
            "Shared researcher interpretation",
        ),
        (
            "05-multi-file/researcher-a/video-11.eaf",
            0,
            "Researcher A multi-file video change",
        ),
        (
            "05-multi-file/researcher-a/session-12.eaf",
            1,
            "Researcher A multi-file session change",
        ),
    )
    for relative_path, annotation_index, replacement in scenarios:
        variant = load(source)
        change_annotation_at(variant, annotation_index, replacement)
        save(variant, collaboration / relative_path)
    write_readme(output, filename, second_cycle_annotation_id)


def generate_topic_suggestion(source: Path, output: Path) -> Path:
    """Add one non-destructive manual scenario for topic-name confirmation."""
    destination = output / "07-topic-suggestion" / source.name
    variant = load(source)
    change_first_value(
        variant,
        "Topic suggestion test: researcher-confirmed prosody annotation",
    )
    save(variant, destination)
    return destination


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--topic-suggestion-only",
        action="store_true",
        help="Add only the topic-suggestion scenario without replacing the suite.",
    )
    arguments = parser.parse_args()
    if arguments.topic_suggestion_only:
        generate_topic_suggestion(arguments.source, arguments.output)
    else:
        generate(arguments.source, arguments.output)


if __name__ == "__main__":
    main()
