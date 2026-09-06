import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.model.association import ElanFileToMedia
from app.model.elan_file import ElanFile
from app.model.elan_file_media import ElanFileMedia
from app.model.file_content import FileContent
from app.utils.database import DatabaseUtils


async def get_project_files_with_media_simple(
    db: AsyncSession, project_id: int
) -> list[dict]:
    """Get all ELAN files for a project with their associated media using simple joins."""
    # Use a simpler approach with explicit joins to avoid lazy loading issues
    stmt = (
        select(
            ElanFile.elan_id,
            ElanFile.file_path,
            ElanFile.filename,
            ElanFileMedia.media_url,
            ElanFileMedia.relative_media_url,
        )
        .join(FileContent, ElanFile.content_id == FileContent.content_id)
        .join(ElanFileToMedia, ElanFile.elan_id == ElanFileToMedia.elan_id)
        .join(ElanFileMedia, ElanFileToMedia.media_id == ElanFileMedia.media_id)
        .where(ElanFile.project_id == project_id)
    )

    result = await db.execute(stmt)
    rows = result.fetchall()

    # Group by elan_id to collect all media for each file
    files_dict = {}
    for row in rows:
        elan_id = row.elan_id
        if elan_id not in files_dict:
            files_dict[elan_id] = {
                "elan_id": row.elan_id,
                "filename": row.filename,
                "file_path": row.file_path,
                "media_filenames": [],
            }

        # Extract media filename
        if row.relative_media_url:
            media_filename = os.path.basename(row.relative_media_url)
        elif row.media_url:
            if row.media_url.startswith("file:///"):
                path_part = row.media_url[8:]  # Remove 'file:///'
                media_filename = os.path.basename(path_part)
            else:
                media_filename = os.path.basename(row.media_url)
        else:
            continue

        if (
            media_filename
            and media_filename not in files_dict[elan_id]["media_filenames"]
        ):
            files_dict[elan_id]["media_filenames"].append(media_filename)

    return list(files_dict.values())


async def get_project_files_with_media(
    db: AsyncSession, project_id: int
) -> list[ElanFile]:
    """Get all ELAN files in a project with their associated media."""
    stmt = (
        select(ElanFile)
        .options(selectinload(ElanFile.media_links).selectinload(ElanFileToMedia.media))
        .where(ElanFile.project_id == project_id)
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def get_media_by_url(db: AsyncSession, media_url: str) -> ElanFileMedia | None:
    """Retrieve a media file by its URL."""
    filters = {"media_url": media_url}
    return await DatabaseUtils.get_one_by_filter(db, ElanFileMedia, filters)


async def create_media_in_db(
    db: AsyncSession,
    media_url: str,
    mime_type: str | None = None,
    relative_media_url: str | None = None,
) -> ElanFileMedia:
    """Create a new media file record in the database."""
    media = ElanFileMedia(
        media_url=media_url,
        mime_type=mime_type,
        relative_media_url=relative_media_url,
    )
    await DatabaseUtils.create(db, media)
    await db.flush()
    return media


async def create_or_get_media_in_db(
    db: AsyncSession,
    media_url: str,
    mime_type: str | None = None,
    relative_media_url: str | None = None,
) -> ElanFileMedia:
    """Get or create a media file by URL."""
    media = await get_media_by_url(db, media_url)
    if media:
        return media
    return await create_media_in_db(db, media_url, mime_type, relative_media_url)


async def get_media_by_id(db: AsyncSession, media_id: int) -> ElanFileMedia | None:
    """Retrieve a media file by its ID."""
    return await DatabaseUtils.get_by_id(db, ElanFileMedia, "media_id", media_id)


async def get_all_media(db: AsyncSession) -> list[ElanFileMedia]:
    """Get all media files."""
    return await DatabaseUtils.get_all(db, ElanFileMedia)


async def delete_orphaned_media(db: AsyncSession) -> int:
    """Delete all media files that are not referenced in ELAN_FILE_TO_MEDIA.

    Returns the number of deleted rows.
    """
    return await DatabaseUtils.delete_fully_orphaned(
        db, ElanFileMedia, ElanFileToMedia, "media_id", "media_id"
    )
