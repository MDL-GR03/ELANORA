"""Judging a filename against a frozen naming standard.

A standard is a pattern whose ``{component}`` placeholders are replaced by each
component's regular expression. A component may also list accepted values:
exact text, a zero-padded numeric range such as ``001-099``, or a
``/pattern/flags`` literal. These are the semantics of the upload page's check
in ``frontend/src/utils/filenameCompliance.js``, except that each component is
read from its own named group, so the order of placeholders does not matter.

Protocol validation depends on this module, so it is part of the validator
release fingerprint.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import PurePosixPath

_RANGE = re.compile(r"^(\d+)-(\d+)$")
_LITERAL = re.compile(r"^/(.*)/([gimsuy]*)$")
_LITERAL_FLAGS = (("i", re.IGNORECASE), ("m", re.MULTILINE), ("s", re.DOTALL))


@dataclass(frozen=True, slots=True)
class FilenameComponent:
    """One named part of a filename."""

    name: str
    regex: str
    accepted_values: Sequence[str]


def compile_standard(
    pattern: str, components: Sequence[FilenameComponent]
) -> re.Pattern[str]:
    """Build the whole-name expression, raising ValueError when unusable."""
    names = [component.name for component in components]
    if len(set(names)) != len(names):
        raise ValueError("component names must be unique")
    misplaced = [name for name in names if pattern.count("{" + name + "}") != 1]
    if misplaced:
        raise ValueError(
            "each component placeholder must appear exactly once: "
            + ", ".join(misplaced)
        )
    expression = pattern
    for index, component in enumerate(components):
        _compile(component.regex or ".+", component.name)
        expression = expression.replace(
            "{" + component.name + "}", f"(?P<c{index}>{component.regex or '.+'})"
        )
    return _compile(expression, "pattern")


def filename_matches(
    pattern: str, components: Sequence[FilenameComponent], filename: str
) -> bool:
    """Whether a filename, ignoring directories and its last extension, complies."""
    name = PurePosixPath(filename).name
    stem = re.sub(r"\.[^/.]+$", "", name)
    match = compile_standard(pattern, components).fullmatch(stem)
    if match is None:
        return False
    return all(
        _component_matches(component, match.group(f"c{index}"))
        for index, component in enumerate(components)
    )


def _compile(expression: str, label: str) -> re.Pattern[str]:
    try:
        return re.compile(expression)
    except re.error as error:
        raise ValueError(f"{label} is not a valid regular expression") from error


def _component_matches(component: FilenameComponent, value: str) -> bool:
    if component.regex and re.fullmatch(component.regex, value) is None:
        return False
    if not component.accepted_values:
        return True
    return any(_accepted(accepted, value) for accepted in component.accepted_values)


def _accepted(accepted: str, value: str) -> bool:
    if accepted == value:
        return True
    literal = _LITERAL.match(accepted)
    if literal is not None:
        flags = 0
        for letter, flag in _LITERAL_FLAGS:
            if letter in literal.group(2):
                flags |= flag
        try:
            return re.search(literal.group(1), value, flags) is not None
        except re.error:
            return False
    bounds = _RANGE.match(accepted.strip())
    if bounds is None:
        return False
    width = len(bounds.group(1))
    if len(value) != width or re.fullmatch(r"[0-9]+", value) is None:
        return False
    return int(bounds.group(1)) <= int(value) <= int(bounds.group(2))
