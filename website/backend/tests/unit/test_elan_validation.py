"""Tests for the upload boundary around ELAN annotation files."""

from tempfile import SpooledTemporaryFile
from types import SimpleNamespace
from typing import Any, BinaryIO, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, UploadFile

from app.api.v1 import git_projects, git_shared
from app.dependency.elan_validation import validate_multiple_elan_files


def upload(filename: str, content: bytes) -> UploadFile:
    """Build an in-memory upload with the same metadata FastAPI provides."""
    stream = SpooledTemporaryFile()  # noqa: SIM115 - UploadFile owns this stream
    stream.write(content)
    stream.seek(0)
    return UploadFile(
        filename=filename, file=cast("BinaryIO", stream), size=len(content)
    )


VALID_EAF = b"""<?xml version="1.0" encoding="UTF-8"?>
<ANNOTATION_DOCUMENT AUTHOR="" DATE="2026-08-31T00:00:00+00:00" FORMAT="3.0" VERSION="3.0">
  <HEADER MEDIA_FILE="" TIME_UNITS="milliseconds"/>
  <TIME_ORDER/>
</ANNOTATION_DOCUMENT>
"""


@pytest.mark.asyncio
async def test_valid_eaf_is_accepted_and_rewound() -> None:
    """Accept a structurally valid EAF and leave it readable downstream."""
    file = upload("annotations.eaf", VALID_EAF)

    result = await validate_multiple_elan_files([file])

    assert result == [file]
    assert await file.read() == VALID_EAF


@pytest.mark.asyncio
async def test_malformed_xml_is_rejected_instead_of_recovered() -> None:
    """Do not silently repair malformed research data during ingestion."""
    file = upload("broken.eaf", b"<ANNOTATION_DOCUMENT><HEADER/><TIME_ORDER>")

    with pytest.raises(HTTPException, match="XML is not well formed"):
        await validate_multiple_elan_files([file])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "filename", ["../escape.eaf", "folder/file.eaf", "folder\\file.eaf"]
)
async def test_path_components_in_upload_name_are_rejected(filename: str) -> None:
    """Keep flat project uploads inside their designated directory."""
    with pytest.raises(HTTPException, match="Invalid ELAN filename"):
        await validate_multiple_elan_files([upload(filename, VALID_EAF)])


@pytest.mark.asyncio
async def test_doctype_is_rejected() -> None:
    """Reject DTD-bearing XML at the public upload boundary."""
    content = b"""<?xml version="1.0"?>
<!DOCTYPE ANNOTATION_DOCUMENT [<!ENTITY example "value">]>
<ANNOTATION_DOCUMENT AUTHOR="" DATE="2026-08-31T00:00:00+00:00" VERSION="3.0">
  <HEADER MEDIA_FILE="" TIME_UNITS="milliseconds"/>
  <TIME_ORDER/>
</ANNOTATION_DOCUMENT>
"""

    with pytest.raises(HTTPException, match="document type declarations"):
        await validate_multiple_elan_files([upload("doctype.eaf", content)])


@pytest.mark.asyncio
async def test_folder_project_import_validates_before_creating_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Do not let the folder-import route bypass the EAF ingestion boundary."""
    create_project = AsyncMock()
    database = MagicMock()
    database.commit = AsyncMock()
    monkeypatch.setattr(
        git_shared.git_service, "init_project_from_folder_upload", create_project
    )
    malformed = upload("broken.eaf", b"<ANNOTATION_DOCUMENT><HEADER/><TIME_ORDER>")

    with pytest.raises(HTTPException) as error:
        await git_projects.init_project_from_folder_upload(
            project_name="research-project",
            description="Research project",
            files=[malformed],
            db=cast("Any", database),
            user=cast("Any", SimpleNamespace(user_id=7, instance_id=11)),
        )

    assert error.value.status_code == 422
    assert error.value.detail["code"] == "invalid_eaf_batch"
    assert error.value.detail["rejected_files"][0]["issue_count"] == 1
    assert error.value.detail["rejected_files"][0]["issues"][0]["code"] == "xml_syntax"
    database.add.assert_called_once()
    database.commit.assert_awaited_once()
    create_project.assert_not_awaited()
