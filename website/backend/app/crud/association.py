from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.centralized_logging import get_logger
from app.core.error_diagnostics import safe_exception_type
from app.model.association import (
    ElanFileToMedia,
    ElanFileToTier,
    ProjectAnnotStandard,
    ProjectCapabilityGrant,
    UserToProject,
)
from app.model.elan_file import ElanFile
from app.model.enums import ProjectCapability
from app.model.project_file_type import ProjectFileType
from app.model.user import User
from app.utils.database import DatabaseUtils

logger = get_logger()

# --- ElanFileToMedia ---


async def add_elan_file_to_media(db: AsyncSession, elan_id: int, media_id: int):
    filters = {"elan_id": elan_id, "media_id": media_id}
    exists = await DatabaseUtils.get_one_by_filter(db, ElanFileToMedia, filters)
    if not exists:
        assoc = ElanFileToMedia(elan_id=elan_id, media_id=media_id)
        await DatabaseUtils.create(db, assoc)
        await db.flush()


async def remove_elan_file_from_media(db: AsyncSession, elan_id: int, media_id: int):
    await DatabaseUtils.delete_by_filter(
        db, ElanFileToMedia, elan_id=elan_id, media_id=media_id
    )


async def update_elan_file_media(
    db: AsyncSession, elan_id: int, old_media_id: int, new_media_id: int
):
    await DatabaseUtils.update_by_filter(
        db,
        ElanFileToMedia,
        {"elan_id": elan_id, "media_id": old_media_id},
        {"media_id": new_media_id},
    )


# --- ElanFileToTier ---


async def add_elan_file_to_tier(db: AsyncSession, elan_id: int, tier_id: int):
    filters = {"elan_id": elan_id, "tier_id": tier_id}
    exists = await DatabaseUtils.get_one_by_filter(db, ElanFileToTier, filters)
    if not exists:
        assoc = ElanFileToTier(elan_id=elan_id, tier_id=tier_id)
        await DatabaseUtils.create(db, assoc)


async def remove_elan_file_from_tier(db: AsyncSession, elan_id: int, tier_id: int):
    await DatabaseUtils.delete_by_filter(
        db, ElanFileToTier, elan_id=elan_id, tier_id=tier_id
    )


async def update_elan_file_tier(
    db: AsyncSession, elan_id: int, old_tier_id: int, new_tier_id: int
):
    await DatabaseUtils.update_by_filter(
        db,
        ElanFileToTier,
        {"elan_id": elan_id, "tier_id": old_tier_id},
        {"tier_id": new_tier_id},
    )


# --- ProjectAnnotStandard ---


async def add_project_annot_standard(
    db: AsyncSession, project_id: int, annot_standard_id: int
):
    filters = {"project_id": project_id, "annot_standard_id": annot_standard_id}
    exists = await DatabaseUtils.get_one_by_filter(db, ProjectAnnotStandard, filters)
    if not exists:
        assoc = ProjectAnnotStandard(
            project_id=project_id, annot_standard_id=annot_standard_id
        )
        await DatabaseUtils.create(db, assoc)


async def remove_project_annot_standard(
    db: AsyncSession, project_id: int, annot_standard_id: int
):
    await DatabaseUtils.delete_by_filter(
        db,
        ProjectAnnotStandard,
        project_id=project_id,
        annot_standard_id=annot_standard_id,
    )


async def update_project_annot_standard(
    db: AsyncSession,
    project_id: int,
    old_annot_standard_id: int,
    new_annot_standard_id: int,
):
    await DatabaseUtils.update_by_filter(
        db,
        ProjectAnnotStandard,
        {"project_id": project_id, "annot_standard_id": old_annot_standard_id},
        {"annot_standard_id": new_annot_standard_id},
    )


# --- UserToProject ---


async def add_user_to_project(db: AsyncSession, user_id: int, project_id: int):
    filters = {"user_id": user_id, "project_id": project_id}
    exists = await DatabaseUtils.get_one_by_filter(db, UserToProject, filters)
    if not exists:
        assoc = UserToProject(user_id=user_id, project_id=project_id)
        await DatabaseUtils.create(db, assoc)


async def update_user_project(
    db: AsyncSession, user_id: int, old_project_id: int, new_project_id: int
):
    await DatabaseUtils.update_by_filter(
        db,
        UserToProject,
        {"user_id": user_id, "project_id": old_project_id},
        {"project_id": new_project_id},
    )


# --- ProjectFileType ---
async def remove_file_type_from_project(
    db: AsyncSession, project_id: int, file_type_id: int
):
    await DatabaseUtils.delete_by_filter(
        db, ProjectFileType, project_id=project_id, file_type_id=file_type_id
    )


async def add_project_file_type(
    db: AsyncSession,
    project_id: int,
    name: str,
    file_type_id: int,
):
    filters = {"project_id": project_id, "name": name}
    exists = await DatabaseUtils.get_one_by_filter(db, ProjectFileType, filters)
    if not exists:
        assoc = ProjectFileType(
            project_id=project_id,
            name=name,
            file_type_id=file_type_id,
        )
        await DatabaseUtils.create(db, assoc)
        await db.flush()
        return assoc
    return exists


async def get_project_file_types(db: AsyncSession, project_id: int):
    return await DatabaseUtils.get_by_filter(
        db,
        ProjectFileType,
        {"project_id": project_id},
        options=[selectinload(ProjectFileType.file_type)],
    )


async def delete_project_file_type(
    db: AsyncSession, project_file_type_id: int, project_id: int
):
    # Delete the association between the project and the project file type
    await DatabaseUtils.delete_by_filter(
        db, ProjectFileType, project_id=project_id, id=project_file_type_id
    )


async def update_project_file_type(
    db: AsyncSession, project_file_type_id: int, update_fields: dict
):
    # Only update name or file_type_id (not extension here)
    allowed = {}
    if "name" in update_fields:
        allowed["name"] = update_fields["name"]
    if "file_type_id" in update_fields:
        allowed["file_type_id"] = update_fields["file_type_id"]
    if allowed:
        await DatabaseUtils.update_by_filter(
            db, ProjectFileType, {"id": project_file_type_id}, allowed
        )


async def get_project_file_type_by_id(db: AsyncSession, project_file_type_id: int):
    return await DatabaseUtils.get_one_by_filter(
        db,
        ProjectFileType,
        {"id": project_file_type_id},
        options=[selectinload(ProjectFileType.file_type)],
    )


async def count_project_file_types_by_file_type_id(
    db: AsyncSession, file_type_id: int
) -> int:
    return await DatabaseUtils.count(
        db, ProjectFileType, {"file_type_id": file_type_id}
    )


async def update_project_file_type_name(
    db: AsyncSession, project_file_type_id: int, name: str
):
    return await DatabaseUtils.update_by_filter(
        db, ProjectFileType, {"id": project_file_type_id}, {"name": name}
    )


async def update_project_file_type_file_type_id(
    db: AsyncSession, project_file_type_id: int, new_file_type_id: int
):
    return await DatabaseUtils.update_by_filter(
        db,
        ProjectFileType,
        {"id": project_file_type_id},
        {"file_type_id": new_file_type_id},
    )


async def get_project_file_type_by_project_and_file_type(
    db, project_id: int, file_type_id: int
):
    """Get the ProjectFileType for a given project and file_type_id."""
    return await DatabaseUtils.get_one_by_filter(
        db, ProjectFileType, {"project_id": project_id, "file_type_id": file_type_id}
    )


async def get_project_file_type_with_file_type(db, project_file_type_id: int):
    result = await db.execute(
        select(ProjectFileType)
        .options(selectinload(ProjectFileType.file_type))
        .where(ProjectFileType.id == project_file_type_id)
    )
    return result.scalar_one_or_none()


# --- Bulk delete for project associations (unchanged) ---


async def delete_project_associations(db: AsyncSession, project_id: int):
    logger.info("Bulk deleting project associations for project_id=%s", project_id)
    try:
        await DatabaseUtils.bulk_delete(
            db, ProjectFileType, ProjectFileType.project_id == project_id
        )
        # ElanFileToProject removed - files are now deleted via cascade from project_id FK
        await DatabaseUtils.bulk_delete(
            db, ProjectAnnotStandard, ProjectAnnotStandard.project_id == project_id
        )
        await DatabaseUtils.bulk_delete(
            db, UserToProject, UserToProject.project_id == project_id
        )
        logger.info("Bulk deleted project associations successfully")
        await db.flush()
    except Exception as e:
        await db.rollback()
        logger.error(
            "Failed to bulk delete project associations for project_id=%s: %s",
            project_id,
            e,
        )


# --- Utility fetchers (unchanged) ---


async def get_elan_ids_for_project(db: AsyncSession, project_id: int) -> list[int]:
    """Get all ELAN file IDs for a project - now uses direct project_id FK."""
    records = await DatabaseUtils.get_by_filter(
        db, ElanFile, {"project_id": project_id}
    )
    return [r.elan_id for r in records]


async def get_tier_ids_for_elan_file(db, elan_id: int) -> list[int]:
    """Get all tier IDs associated with an ELAN file."""
    records = await DatabaseUtils.get_by_filter(
        db, ElanFileToTier, {"elan_id": elan_id}
    )
    return [r.tier_id for r in records]


async def get_project_users(db: AsyncSession, project_id: int) -> list[dict]:
    """Get all users associated with a project with their permissions."""
    stmt = (
        select(UserToProject, User)
        .join(User, UserToProject.user_id == User.user_id)
        .where(UserToProject.project_id == project_id)
    )

    result = await db.execute(stmt)
    grants = (
        await db.execute(
            select(ProjectCapabilityGrant).where(
                ProjectCapabilityGrant.project_id == project_id
            )
        )
    ).scalars()
    capabilities_by_user: dict[int, list[str]] = {}
    for grant in grants:
        capabilities_by_user.setdefault(grant.user_id, []).append(
            ProjectCapability(grant.capability).value
        )
    return [
        {
            "user_id": user_to_project.user_id,
            "username": user.username,
            "email": user.email,
            "permission": user_to_project.permission,
            "capabilities": sorted(
                capabilities_by_user.get(user_to_project.user_id, [])
            ),
        }
        for user_to_project, user in result.all()
    ]


async def remove_user_from_project(
    db: AsyncSession, user_id: int, project_id: int
) -> bool:
    """Remove a user from a project."""
    try:
        result = await DatabaseUtils.bulk_delete(
            db,
            UserToProject,
            (UserToProject.user_id == user_id)
            & (UserToProject.project_id == project_id),
        )
        await db.commit()
        return result > 0
    except Exception as e:
        logger.error(
            "Failed to remove a project member; error_type=%s",
            safe_exception_type(e),
        )
        await db.rollback()
        return False
