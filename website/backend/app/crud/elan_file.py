from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.crud.annotation import (
    delete_unused_annotation_values,
)
from app.crud.association import add_elan_file_to_media
from app.crud.elan_file_media import (
    create_or_get_media_in_db,
    delete_orphaned_media,
)
from app.crud.file_content import get_or_create_file_content
from app.elan.persistence import PersistedEafFile
from app.model.association import ElanFileToMedia, ElanFileToTier
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.tier_group import TierGroup
from app.model.user import User
from app.utils.database import DatabaseUtils
from app.utils.validation import ValidationUtils

logger = get_logger()


async def get_orphan_elan_files_by_project(
    db: AsyncSession, project_id: int
) -> list[ElanFile]:
    """Get ELAN files that belong directly to a project via project_id FK."""
    logger.info("Fetching ELAN files for project_id=%s", project_id)
    filters = {"project_id": project_id}
    elan_files = await DatabaseUtils.get_by_filter(
        db, ElanFile, filters, options=[selectinload(ElanFile.file_content)]
    )
    logger.info("Found %d ELAN files for project_id=%s", len(elan_files), project_id)
    return elan_files


async def delete_elan_file_associations(db: AsyncSession, elan_id: int) -> None:
    """Delete ELAN file associations - now only handles media/tier links since project link is direct FK."""
    logger.info("Attempting to delete ELAN file associations for elan_id=%s", elan_id)
    try:
        await DatabaseUtils.bulk_delete(
            db, ElanFileToTier, ElanFileToTier.elan_id == elan_id
        )
        # ElanFileToProject removed - project association handled by CASCADE on project_id FK
        await DatabaseUtils.bulk_delete(
            db, ElanFileToMedia, ElanFileToMedia.elan_id == elan_id
        )
        await DatabaseUtils.delete_by_filter(db, TierGroup, elan_id=elan_id)
        logger.info("Deleted ELAN file associations for elan_id=%s", elan_id)
    except Exception as error:
        logger.error(
            "Failed to delete ELAN file associations; elan_id=%s error_type=%s",
            elan_id,
            safe_exception_type(error),
        )
        raise


async def get_elan_file_by_id(db: AsyncSession, elan_id: int) -> ElanFile | None:
    """Retrieve an ELAN file by ID."""
    return await DatabaseUtils.get_by_id(
        db, ElanFile, "elan_id", elan_id, options=[selectinload(ElanFile.file_content)]
    )


async def get_elan_file_by_filename(db: AsyncSession, filename: str) -> ElanFile | None:
    """Retrieve an ELAN file by filename."""
    stmt = (
        select(ElanFile)
        .join(FileContent)
        .where(ElanFile.filename == filename)
        .options(selectinload(ElanFile.file_content))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_elan_files_by_user(db: AsyncSession, user_id: int) -> list[ElanFile]:
    """Get all ELAN files for a specific user."""
    stmt = (
        select(ElanFile)
        .join(FileContent)
        .where(FileContent.user_id == user_id)
        .options(selectinload(ElanFile.file_content))
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def check_elan_file_exists_by_filename(db: AsyncSession, filename: str) -> bool:
    """Check if an ELAN file with the given filename exists."""
    stmt = select(ElanFile).where(ElanFile.filename == filename)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def get_elan_file_by_filename_and_project(
    db: AsyncSession, filename: str, project_id: int
) -> ElanFile | None:
    """Retrieve an ELAN file by filename and project ID."""
    stmt = (
        select(ElanFile)
        .join(FileContent)
        .where(ElanFile.filename == filename, ElanFile.project_id == project_id)
        .options(selectinload(ElanFile.file_content))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def check_elan_file_exists_by_filename_and_project(
    db: AsyncSession, filename: str, project_id: int
) -> bool:
    """Check if an ELAN file with the given filename exists in a specific project."""
    stmt = (
        select(ElanFile)
        .join(FileContent)
        .where(ElanFile.filename == filename, ElanFile.project_id == project_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


async def create_elan_file_in_db(
    db: AsyncSession,
    filename: str,
    file_path: str,
    file_size: int,
    user_id: int,
    project_id: int,
    last_modified: datetime,
) -> ElanFile:
    """Create a new ELAN file record in the database with project association."""
    ValidationUtils.validate_user_id(user_id)
    sanitized_filename = ValidationUtils.sanitize_filename(filename)

    # Use existing file content CRUD to handle deduplication
    file_content = await get_or_create_file_content(
        db=db,
        filename=sanitized_filename,
        file_size=file_size,
        file_path=file_path,
        user_id=user_id,
    )

    # Then create the ElanFile with the content_id
    elan_file = ElanFile(
        content_id=file_content.content_id,
        project_id=project_id,
        filename=sanitized_filename,
        file_path=file_path,
        last_modified=last_modified,
    )

    elan_file = await DatabaseUtils.create(db, elan_file)
    await db.flush()
    return elan_file


async def delete_elan_file_by_id(db: AsyncSession, elan_id: int) -> bool:
    """Delete an ELAN file by ID."""
    try:
        count = await DatabaseUtils.delete_by_filter(db, ElanFile, elan_id=elan_id)
        return count > 0
    except Exception:
        await db.rollback()
        return False


async def get_all_elan_files(db: AsyncSession) -> list[ElanFile]:
    """Get all ELAN files."""
    return await DatabaseUtils.get_all(
        db, ElanFile, options=[selectinload(ElanFile.file_content)]
    )


# --- ELAN_FILE_TO_TIER ASSOCIATION CRUD ---


async def get_tiers_for_elan_file(db: AsyncSession, elan_id: int) -> list[int]:
    """Get all tier_ids associated with an ELAN file."""
    filters = {"elan_id": elan_id}
    associations = await DatabaseUtils.get_by_filter(db, ElanFileToTier, filters)
    return [assoc.tier_id for assoc in associations]


async def add_elan_file_to_tier(db: AsyncSession, elan_id: int, tier_id: int) -> None:
    """Add association between ELAN file and tier if not exists."""
    filters = {"elan_id": elan_id, "tier_id": tier_id}
    exists = await DatabaseUtils.get_one_by_filter(db, ElanFileToTier, filters)
    if not exists:
        assoc = ElanFileToTier(elan_id=elan_id, tier_id=tier_id)
        await DatabaseUtils.create(db, assoc)


async def remove_elan_file_to_tier(
    db: AsyncSession, elan_id: int, tier_id: int
) -> None:
    """Remove association between ELAN file and tier."""
    await DatabaseUtils.bulk_delete(
        db,
        ElanFileToTier,
        (ElanFileToTier.elan_id == elan_id) & (ElanFileToTier.tier_id == tier_id),
    )


async def sync_elan_file_to_tiers(
    db: AsyncSession, elan_id: int, new_tier_ids: list[int]
) -> None:
    """Synchronize ELAN file associations with tiers.

    Args:
        db: Database session
        elan_id: ID of the ELAN file
        new_tier_ids: List of tier IDs to associate with the file

    """
    current_tier_ids = set(await get_tiers_for_elan_file(db, elan_id))
    new_tier_ids_set = set(new_tier_ids)

    # Add new associations
    for tier_id in new_tier_ids_set - current_tier_ids:
        assoc = ElanFileToTier(elan_id=elan_id, tier_id=tier_id)
        await DatabaseUtils.create(db, assoc)

    # Remove old associations
    for tier_id in current_tier_ids - new_tier_ids_set:
        await DatabaseUtils.delete_by_filter(
            db, ElanFileToTier, elan_id=elan_id, tier_id=tier_id
        )


# --- ELAN_FILE_TO_PROJECT ASSOCIATION CRUD ---


async def get_projects_for_elan_file(db: AsyncSession, elan_id: int) -> list[int]:
    """Get the project_id associated with an ELAN file."""
    # With new schema, each ELAN file belongs to only one project
    elan_file = await DatabaseUtils.get_by_id(db, ElanFile, "elan_id", elan_id)
    if elan_file and elan_file.project_id:
        return [elan_file.project_id]
    return []


async def delete_elan_file_full(db: AsyncSession, elan_id: int) -> bool:
    """Delete an ELAN file and all related associations, then clean up orphaned media.

    Returns True if the file was deleted, False otherwise.
    """
    logger.info(f"Full deletion for ELAN file ID: {elan_id}")
    elan_file_obj = await get_elan_file_by_id(db, elan_id)
    if not elan_file_obj:
        logger.warning("ELAN file was not found during deletion")
        return False

    await delete_elan_file_associations(db, elan_id)

    # ELAN_FILE has a direct, non-null project foreign key. There is no
    # many-to-many ownership relation to preserve after this point.
    logger.info("Deleting an ELAN file row")
    await db.delete(elan_file_obj)
    await db.flush()

    deleted_count = await delete_orphaned_media(db)
    await delete_unused_annotation_values(db)
    logger.info("Deleted %s orphaned media records", deleted_count)
    return True


async def store_elan_file_data_in_db(
    db: AsyncSession,
    file_info: PersistedEafFile,
    user_id: int,
    project_id: int,
) -> int:
    """Store parsed ELAN file data in the database and sync associations.

    Returns the elan_id.
    """
    # Check if file already exists in this project
    if await check_elan_file_exists_by_filename_and_project(
        db, file_info["filename"], project_id
    ):
        existing_file = await get_elan_file_by_filename_and_project(
            db, file_info["filename"], project_id
        )
        if existing_file:
            file_content = await get_or_create_file_content(
                db=db,
                filename=file_info["filename"],
                file_size=file_info["file_size"],
                file_path=file_info["file_path"],
                user_id=user_id,
            )
            existing_file.content_id = file_content.content_id
            existing_file.filename = ValidationUtils.sanitize_filename(
                file_info["filename"]
            )
            existing_file.file_path = file_info["file_path"]
            existing_file.last_modified = file_info["last_modified"]
            # File already exists in this project, no need to add association
            # Sync media associations for existing file
            for media in file_info.get("media", []):
                media_obj = await create_or_get_media_in_db(
                    db,
                    media_url=media["media_url"],
                    mime_type=media["mime_type"],
                    relative_media_url=media["relative_media_url"],
                )
                await add_elan_file_to_media(
                    db, existing_file.elan_id, media_obj.media_id
                )
            return existing_file.elan_id

    # Create ELAN file record
    elan_file_obj = await create_elan_file_in_db(
        db=db,
        filename=file_info["filename"],
        file_path=file_info["file_path"],
        file_size=file_info["file_size"],
        user_id=user_id,
        project_id=project_id,
        last_modified=file_info["last_modified"],
    )

    # No need to sync ELAN_FILE_TO_PROJECT - project_id FK handles association

    # Store media descriptors and associations
    for media in file_info.get("media", []):
        media_obj = await create_or_get_media_in_db(
            db,
            media_url=media["media_url"],
            mime_type=media["mime_type"],
            relative_media_url=media["relative_media_url"],
        )
        await add_elan_file_to_media(db, elan_file_obj.elan_id, media_obj.media_id)

    # Create TierGroup entry for this ELAN file and project
    tier_group = TierGroup(
        project_id=project_id,
        elan_file_name=file_info["filename"],
        section_id=None,
        elan_id=elan_file_obj.elan_id,
    )
    await DatabaseUtils.create(db, tier_group)

    return elan_file_obj.elan_id


async def get_elan_files_by_project(
    db: AsyncSession, project_id: int
) -> list[tuple[ElanFile, str]]:
    """Get all ELAN files for a specific project, with user info joined."""
    stmt = (
        select(ElanFile, User.username)
        .join(FileContent, ElanFile.content_id == FileContent.content_id)
        .join(User, FileContent.user_id == User.user_id)
        .where(ElanFile.project_id == project_id)
        .options(selectinload(ElanFile.file_content))
    )
    return await DatabaseUtils.get_with_join(db, stmt)


async def update_elan_file_name(
    db: AsyncSession, elan_id: int, new_filename: str
) -> ElanFile | None:
    """Update the filename of an ELAN file by updating its FileContent record."""
    logger.info(
        "Updating filename for elan_id=%s to new_filename=%s", elan_id, new_filename
    )

    # Get the ELAN file with its content
    stmt = (
        select(ElanFile)
        .options(selectinload(ElanFile.file_content))
        .where(ElanFile.elan_id == elan_id)
    )
    result = await db.execute(stmt)
    elan_file = result.scalar_one_or_none()

    if not elan_file:
        logger.warning("ELAN file not found for elan_id=%s", elan_id)
        return None

    old_filename = elan_file.filename
    logger.info(
        "Changing filename from %s to %s for elan_id=%s",
        old_filename,
        new_filename,
        elan_id,
    )

    elan_file.filename = ValidationUtils.sanitize_filename(new_filename)

    # Update the file_path in the ElanFile record to reflect the new filename
    # Assuming file_path format is like "project/elan_files/filename.eaf"
    old_file_path = elan_file.file_path
    # Replace the old filename in the path with the new one
    if "/" in old_file_path:
        path_parts = old_file_path.split("/")
        path_parts[-1] = ValidationUtils.sanitize_filename(
            new_filename
        )  # Replace the last part (filename)
        new_file_path = "/".join(path_parts)
    else:
        # If no path separators, just use the new filename
        new_file_path = ValidationUtils.sanitize_filename(new_filename)

    elan_file.file_path = new_file_path
    logger.info(
        "Updated file_path from %s to %s for elan_id=%s",
        old_file_path,
        new_file_path,
        elan_id,
    )

    await db.flush()

    logger.info("Successfully updated filename for elan_id=%s", elan_id)
    return elan_file


async def get_elan_file_name_by_id(db: AsyncSession, elan_id: int) -> str | None:
    """Get the current filename of an ELAN file."""
    stmt = select(ElanFile.filename).where(ElanFile.elan_id == elan_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
