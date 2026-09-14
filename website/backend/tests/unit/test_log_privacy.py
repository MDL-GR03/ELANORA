"""Regression tests preventing sensitive values from entering application logs."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from lxml import etree

import app.crud.annotation_value as annotation_value_module
import app.service.user as user_service_module
import app.utils.database as database_module
import app.utils.file_processing as file_processing_module
import app.utils.validation as validation_module
from app.model.accepted_value import AcceptedValue
from app.service.user import UserService
from app.utils.database import DatabaseUtils
from app.utils.file_processing import ElanFileProcessor, XmlAttributeExtractor
from app.utils.validation import ValidationUtils

SENSITIVE_VALUE = "participant-secret-annotation@example.org"


def _rendered_calls(logger: Mock) -> str:
    return repr(logger.method_calls)


@pytest.mark.asyncio
async def test_generic_database_logs_exclude_record_and_filter_values(
    monkeypatch,
) -> None:
    logger = Mock()
    monkeypatch.setattr(database_module, "logger", logger)
    result = Mock()
    result.scalar_one_or_none.return_value = None
    result.scalars.return_value.all.return_value = []
    result.rowcount = 0
    session = SimpleNamespace(execute=AsyncMock(return_value=result), add=Mock())

    await DatabaseUtils.get_by_id(session, AcceptedValue, "value", SENSITIVE_VALUE)
    await DatabaseUtils.exists(session, AcceptedValue, "value", SENSITIVE_VALUE)
    await DatabaseUtils.create(session, AcceptedValue(value=SENSITIVE_VALUE))
    await DatabaseUtils.delete_by_filter(session, AcceptedValue, value=SENSITIVE_VALUE)
    await DatabaseUtils.bulk_delete(
        session, AcceptedValue, AcceptedValue.value == SENSITIVE_VALUE
    )

    assert SENSITIVE_VALUE not in _rendered_calls(logger)


@pytest.mark.asyncio
async def test_annotation_value_logs_contain_counts_not_annotation_text(
    monkeypatch,
) -> None:
    logger = Mock()
    monkeypatch.setattr(annotation_value_module, "logger", logger)
    monkeypatch.setattr(
        annotation_value_module.DatabaseUtils,
        "get_by_filter",
        AsyncMock(
            side_effect=[
                [],
                [SimpleNamespace(annotation_value=SENSITIVE_VALUE, value_id=1)],
            ]
        ),
    )
    monkeypatch.setattr(
        annotation_value_module.DatabaseUtils, "bulk_insert", AsyncMock()
    )
    session = SimpleNamespace(flush=AsyncMock())

    result = await annotation_value_module.bulk_get_or_create_annotation_values(
        session,
        [{"annotations": [{"annotation_value": SENSITIVE_VALUE}]}],
    )

    assert result == {SENSITIVE_VALUE: 1}
    assert SENSITIVE_VALUE not in _rendered_calls(logger)


def test_xml_extraction_logs_exclude_annotation_text(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(file_processing_module, "logger", logger)
    annotation = etree.fromstring(
        f"<ALIGNABLE_ANNOTATION ANNOTATION_ID='a1' TIME_SLOT_REF1='ts1' "
        f"TIME_SLOT_REF2='ts2'><ANNOTATION_VALUE>{SENSITIVE_VALUE}"
        "</ANNOTATION_VALUE></ALIGNABLE_ANNOTATION>"
    )

    extracted = XmlAttributeExtractor.get_alignable_annotation_attributes(
        annotation, {"ts1": 0, "ts2": 1000}
    )

    assert extracted is not None
    assert extracted["annotation_value"] == SENSITIVE_VALUE
    assert SENSITIVE_VALUE not in _rendered_calls(logger)


def test_file_validation_logs_exclude_sensitive_path(monkeypatch, tmp_path) -> None:
    logger = Mock()
    monkeypatch.setattr(file_processing_module, "logger", logger)
    sensitive_file = tmp_path / f"{SENSITIVE_VALUE}.eaf"
    sensitive_file.write_text("<ANNOTATION_DOCUMENT />", encoding="utf-8")

    validated = ElanFileProcessor.validate_elan_file(str(sensitive_file))
    info = ElanFileProcessor.get_file_info(validated)

    assert info["filename"] == sensitive_file.name
    assert SENSITIVE_VALUE not in _rendered_calls(logger)


def test_validation_logs_exclude_string_and_filename_values(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(validation_module, "logger", logger)

    assert ValidationUtils.is_valid_string(SENSITIVE_VALUE)
    assert ValidationUtils.sanitize_filename(SENSITIVE_VALUE) == SENSITIVE_VALUE
    assert ValidationUtils.is_filename_compliant(None, SENSITIVE_VALUE)

    assert SENSITIVE_VALUE not in _rendered_calls(logger)


@pytest.mark.asyncio
async def test_authentication_logs_exclude_login_identifier(monkeypatch) -> None:
    logger = Mock()
    monkeypatch.setattr(user_service_module, "logger", logger)
    monkeypatch.setattr(
        user_service_module,
        "get_user_by_username_or_email",
        AsyncMock(return_value=None),
    )

    result = await UserService.authenticate_user(
        SimpleNamespace(), SENSITIVE_VALUE, "unused-password"
    )

    assert result is None
    assert SENSITIVE_VALUE not in _rendered_calls(logger)
