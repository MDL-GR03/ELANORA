"""File Content CRUD operations for normalized file storage."""

import hashlib
from datetime import datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.centralized_logging import get_logger
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.utils.database import DatabaseUtils
from app.utils.file_processing import make_path_absolute_from_projects

logger = get_logger()


def calculate_file_hash(file_path: str) -> str:
    """Calculate SHA-256 hash of file content for deduplication."""
    hash_sha256 = hashlib.sha256()
    file_path_obj = Path(file_path)

    with file_path_obj.open("rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)

    return hash_sha256.hexdigest()


async def get_file_content_by_hash(
    db: AsyncSession, content_hash: str
) -> FileContent | None:
    """Get file content by hash."""
    stmt = select(FileContent).where(FileContent.content_hash == content_hash)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_file_content_by_id(
    db: AsyncSession, content_id: int
) -> FileContent | None:
    """Get file content by ID."""
    return await DatabaseUtils.get_by_id(db, FileContent, "content_id", content_id)


async def create_file_content(
    db: AsyncSession,
    filename: str,
    file_size: int,
    content_hash: str,
    user_id: int | None = None,
) -> FileContent:
    """Create a new file content record."""
    file_content = FileContent(
        filename=filename,
        file_size=file_size,
        content_hash=content_hash,
        user_id=user_id,
        created_at=datetime.now(),
    )

    file_content = await DatabaseUtils.create(db, file_content)
    await db.flush()

    logger.info("Created one file-content record")
    return file_content


async def get_or_create_file_content(
    db: AsyncSession,
    filename: str,
    file_size: int,
    file_path: str,
    user_id: int | None = None,
) -> FileContent:
    """Get existing file content or create new one based on content hash.

    Automatically handles both absolute and relative file paths.
    Relative paths are converted to absolute for file operations.
    """
    # Convert relative path to absolute if needed for file operations
    if not Path(file_path).is_absolute():
        absolute_path = make_path_absolute_from_projects(file_path)
        logger.debug("Resolved a relative content path")
    else:
        absolute_path = file_path
        logger.debug("Using a caller-provided absolute content path")

    # Calculate hash using absolute path
    content_hash = calculate_file_hash(absolute_path)

    # Check if content already exists
    existing_content = await get_file_content_by_hash(db, content_hash)

    if existing_content:
        logger.info("Reusing an existing file-content record")
        return existing_content

    # Create new content record
    return await create_file_content(db, filename, file_size, content_hash, user_id)


async def delete_file_content(db: AsyncSession, content_id: int) -> bool:
    """Delete file content by ID."""
    try:
        result = await DatabaseUtils.delete_by_id(
            db, FileContent, "content_id", content_id
        )
        if result:
            logger.info("Deleted one file-content record")
        return result
    except Exception as e:
        logger.error("Failed to delete file content; error_type=%s", type(e).__name__)
        return False


async def get_file_contents_by_user(
    db: AsyncSession, user_id: int
) -> list[FileContent]:
    """Get all file contents created by a specific user."""
    filters = {"user_id": user_id}
    return await DatabaseUtils.get_by_filter(db, FileContent, filters)


async def get_orphaned_file_contents(db: AsyncSession) -> list[FileContent]:
    """Get file contents that are not referenced by any ELAN files."""
    stmt = select(FileContent).where(
        ~FileContent.content_id.in_(select(ElanFile.content_id).distinct())
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def cleanup_orphaned_file_contents(db: AsyncSession) -> int:
    """Delete file contents that are not referenced by any ELAN files."""
    orphaned_contents = await get_orphaned_file_contents(db)
    deleted_count = 0

    for content in orphaned_contents:
        if await delete_file_content(db, content.content_id):
            deleted_count += 1

    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} orphaned file contents")

    return deleted_count
