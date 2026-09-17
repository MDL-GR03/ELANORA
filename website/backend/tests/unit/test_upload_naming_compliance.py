"""Uploaded filenames are judged against the project's naming standard."""

from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest

import app.service.upload_naming_compliance as compliance
from app.schema.protocol import ProtocolRules
from app.schema.responses.project_naming_standard import (
    NamingComponentResponse,
    NamingStandardResponse,
)
from app.service.upload_naming_compliance import (
    FilenameNotCompliantError,
    assert_filenames_comply,
    enforce_upload_naming_standard,
    resolve_upload_naming_standard,
)

STANDARD: dict[str, Any] = {
    "pattern": "{subject}-{session}",
    "components": [{"name": "subject"}, {"name": "session"}],
}


def _standard(pattern: str, *names: str) -> NamingStandardResponse:
    return NamingStandardResponse(
        id=7,
        project_id=1,
        name="Standard",
        project_file_type_id=2,
        file_type_id=3,
        file_type_name="ELAN",
        pattern=pattern,
        components=[
            NamingComponentResponse(
                id=index,
                name=name,
                regex=".+",
                order=index,
                accepted_values=[],
                project_file_type_id=2,
            )
            for index, name in enumerate(names, start=1)
        ],
    )


def _patch_lookup(
    monkeypatch: pytest.MonkeyPatch,
    *,
    location_id: int | None = 3,
    effective: list[Any] | None = None,
    full: NamingStandardResponse | None = None,
) -> None:
    monkeypatch.setattr(
        compliance, "get_location_id_by_name", lambda _name: location_id
    )
    monkeypatch.setattr(
        compliance,
        "get_effective_standards_for_project",
        AsyncMock(return_value=effective if effective is not None else []),
    )
    monkeypatch.setattr(
        compliance, "get_standard_with_components_full", AsyncMock(return_value=full)
    )


def test_a_compliant_filename_is_accepted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        compliance.ValidationUtils, "is_filename_compliant", lambda _s, _f: True
    )
    assert_filenames_comply(STANDARD, ["subject-01.eaf"])


def test_a_non_compliant_filename_names_itself_and_the_pattern(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The researcher has to know which file to rename, and to what shape."""
    monkeypatch.setattr(
        compliance.ValidationUtils, "is_filename_compliant", lambda _s, _f: False
    )

    with pytest.raises(FilenameNotCompliantError) as refused:
        assert_filenames_comply(STANDARD, ["good.eaf"])

    assert refused.value.filename == "good.eaf"
    assert refused.value.pattern == "{subject}-{session}"
    assert "good.eaf" in str(refused.value)


def test_the_first_offending_file_is_the_one_reported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        compliance.ValidationUtils,
        "is_filename_compliant",
        lambda _s, filename: filename != "second.eaf",
    )

    with pytest.raises(FilenameNotCompliantError) as refused:
        assert_filenames_comply(STANDARD, ["first.eaf", "second.eaf", "third.eaf"])

    assert refused.value.filename == "second.eaf"


def test_a_missing_filename_is_rejected_as_an_invalid_request() -> None:
    with pytest.raises(ValueError, match="missing a filename") as refused:
        assert_filenames_comply(STANDARD, [None])
    assert not isinstance(refused.value, FilenameNotCompliantError)


@pytest.mark.asyncio
async def test_no_configured_location_means_no_standard(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lookup(monkeypatch, location_id=None)
    assert await resolve_upload_naming_standard(Mock(), 1) is None


@pytest.mark.asyncio
async def test_a_project_without_an_effective_standard_resolves_to_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lookup(monkeypatch, effective=[])
    assert await resolve_upload_naming_standard(Mock(), 1) is None


@pytest.mark.asyncio
async def test_the_resolved_standard_carries_its_pattern_and_components(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lookup(
        monkeypatch,
        effective=[Mock(naming_standard_id=7)],
        full=_standard("{subject}", "subject"),
    )

    resolved = await resolve_upload_naming_standard(Mock(), 1)

    assert resolved is not None
    assert resolved["pattern"] == "{subject}"
    assert [component["name"] for component in resolved["components"]] == ["subject"]


@pytest.mark.asyncio
async def test_an_unconfigured_project_accepts_any_filename(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_lookup(monkeypatch, effective=[])
    await enforce_upload_naming_standard(
        Mock(), 1, ["anything at all.eaf"], protocol_rules=None
    )


@pytest.mark.asyncio
async def test_a_configuration_failure_is_reported_as_a_data_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A broken lookup must not be mistaken for a badly named file."""
    monkeypatch.setattr(compliance, "get_location_id_by_name", lambda _name: 3)
    monkeypatch.setattr(
        compliance,
        "get_effective_standards_for_project",
        AsyncMock(side_effect=RuntimeError("database unavailable")),
    )

    with pytest.raises(ValueError, match="data issue") as refused:
        await enforce_upload_naming_standard(
            Mock(), 1, ["subject-01.eaf"], protocol_rules=None
        )

    assert not isinstance(refused.value, FilenameNotCompliantError)


@pytest.mark.asyncio
async def test_a_non_compliant_upload_is_not_reported_as_a_data_issue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The previous implementation swallowed this into a generic data error."""
    _patch_lookup(
        monkeypatch,
        effective=[Mock(naming_standard_id=7)],
        full=_standard("{subject}", "subject"),
    )
    monkeypatch.setattr(
        compliance.ValidationUtils, "is_filename_compliant", lambda _s, _f: False
    )

    with pytest.raises(FilenameNotCompliantError) as refused:
        await enforce_upload_naming_standard(
            Mock(), 1, ["wrong name.eaf"], protocol_rules=None
        )

    assert refused.value.filename == "wrong name.eaf"
    assert "data issue" not in str(refused.value)


def _refusing_legacy_standard(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_lookup(
        monkeypatch,
        effective=[Mock(naming_standard_id=7)],
        full=_standard("{subject}-{session}", "subject", "session"),
    )
    monkeypatch.setattr(
        compliance.ValidationUtils, "is_filename_compliant", lambda _s, _f: False
    )


@pytest.mark.asyncio
async def test_a_pinned_filename_standard_replaces_the_legacy_setting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _refusing_legacy_standard(monkeypatch)
    rules = ProtocolRules(
        filename_standard={
            "name": "Any",
            "pattern": "{name}",
            "components": [{"name": "name"}],
        }
    )

    await enforce_upload_naming_standard(
        Mock(), 1, ["wrong name.eaf"], protocol_rules=rules
    )


@pytest.mark.asyncio
async def test_a_pinned_protocol_without_filename_rules_keeps_the_legacy_check(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pinning a content-only protocol must not silently drop filename checks."""
    _refusing_legacy_standard(monkeypatch)

    with pytest.raises(FilenameNotCompliantError):
        await enforce_upload_naming_standard(
            Mock(), 1, ["wrong name.eaf"], protocol_rules=ProtocolRules()
        )
