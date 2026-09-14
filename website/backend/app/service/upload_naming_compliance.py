"""Checking uploaded filenames against a project's effective naming standard.

Projects may pin a filename standard for the upload page. Resolving that
standard and judging a filename against it are separate concerns: failing to
read the configuration is an installation problem, while a filename that does
not match is a normal, reportable outcome the researcher can act on.
"""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.core.effective_naming_standard_locations import get_location_id_by_name
from app.core.error_diagnostics import safe_exception_type
from app.crud.effective_naming_standard import get_effective_standards_for_project
from app.crud.project_naming_standard import get_standard_with_components_full
from app.utils.validation import ValidationUtils

logger = get_logger()

UPLOAD_LOCATION_NAME = "uploadPage"


class FilenameNotCompliantError(ValueError):
    """An uploaded filename does not match the project's naming standard.

    This is a decision about the submission, not a fault in the installation,
    so it carries enough detail for the researcher to rename the file.
    """

    def __init__(self, filename: str, pattern: str | None = None) -> None:
        super().__init__(
            f"Filename '{filename}' does not comply with the project's naming standard."
        )
        self.filename = filename
        self.pattern = pattern


async def resolve_upload_naming_standard(
    db: AsyncSession, project_id: int
) -> dict[str, Any] | None:
    """Return the naming standard for uploads, or None if none is configured."""
    location_id = get_location_id_by_name(UPLOAD_LOCATION_NAME)
    if location_id is None:
        logger.warning("No configured upload location; filenames will not be checked")
        return None

    effective_standards = await get_effective_standards_for_project(
        db, project_id, location_id
    )
    if not effective_standards:
        logger.info("No effective naming standard applies to uploads")
        return None

    effective = effective_standards[0]
    full_standard = await get_standard_with_components_full(
        db, effective.naming_standard_id
    )
    if not full_standard:
        logger.warning("The configured naming standard could not be loaded")
        return None

    return {
        "pattern": full_standard["pattern"],
        "components": full_standard["components"],
    }


def assert_filenames_comply(
    standard: dict[str, Any] | None, filenames: list[str | None]
) -> None:
    """Raise for the first filename that does not match the standard."""
    for filename in filenames:
        if not filename:
            raise ValueError("Uploaded file is missing a filename")
        if not ValidationUtils.is_filename_compliant(standard, filename):
            logger.warning("An uploaded filename does not comply with the standard")
            raise FilenameNotCompliantError(
                filename, pattern=(standard or {}).get("pattern")
            )
    logger.info("All %s uploaded filenames are compliant", len(filenames))


async def enforce_upload_naming_standard(
    db: AsyncSession, project_id: int, filenames: list[str | None]
) -> None:
    """Refuse an upload whose filenames do not match the project's standard."""
    try:
        standard = await resolve_upload_naming_standard(db, project_id)
    except Exception as error:
        # Only a failure to read the configuration is a data issue. A filename
        # that simply does not comply is decided below and reported as itself.
        logger.error(
            "Could not resolve the upload naming standard; error_type=%s",
            safe_exception_type(error),
        )
        raise ValueError(
            "Filename compliance check failed due to a data issue"
        ) from error

    assert_filenames_comply(standard, filenames)
