from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.centralized_logging import get_logger
from app.model.association import UserToProject
from app.model.enums import ProjectPermission
from app.model.project import Project
from app.utils.database import DatabaseUtils

logger = get_logger()


async def create_project_db(
    db: AsyncSession,
    project_name: str,
    description: str,
    project_path: str,
    instance_id: int,
    creator_user_id: int,
) -> Project:
    if description is not None and description.strip() == "":
        description = None
    project = Project(
        project_name=project_name,
        description=description,
        project_path=project_path,
        instance_id=instance_id,
    )
    await DatabaseUtils.create(db, project)
    await db.flush()

    user_to_project = UserToProject(
        project_id=project.project_id,
        user_id=creator_user_id,
        permission=ProjectPermission.OWNER,
    )
    await DatabaseUtils.create(db, user_to_project)
    return project


async def get_project_name_by_id(db: AsyncSession, project_id: int) -> str | None:
    project = await DatabaseUtils.get_by_id(db, Project, "project_id", project_id)
    if project:
        return project.project_name
    return None


async def get_project_by_name(db: AsyncSession, project_name: str) -> Project | None:
    filters = {"project_name": project_name, "deleted_at": None}
    return await DatabaseUtils.get_one_by_filter(db, Project, filters)


async def get_project_by_id(db: AsyncSession, project_id: int) -> Project | None:
    return await DatabaseUtils.get_one_by_filter(
        db, Project, {"project_id": project_id, "deleted_at": None}
    )


async def get_project_id_by_name(db: AsyncSession, project_name: str) -> int | None:
    project = await get_project_by_name(db, project_name)
    if project:
        return project.project_id
    return None


async def delete_project_db(db: AsyncSession, project_name: str) -> None:
    project = await get_project_by_name(db, project_name)
    if project:
        # Retention-driven physical deletion is a separate privileged workflow.
        project.deleted_at = datetime.now(UTC)
        await db.flush()


async def restore_project_db(db: AsyncSession, project_name: str) -> Project:
    """Reactivate a retained project after its recovery cache is restored."""
    project = (
        await db.execute(
            select(Project).where(
                Project.project_name == project_name,
                Project.deleted_at.is_not(None),
            )
        )
    ).scalar_one_or_none()
    if project is None:
        raise ValueError("No retained deleted project exists with this name")
    project.deleted_at = None
    await db.flush()
    return project


async def list_projects_by_instance(
    db: AsyncSession, instance_id: int
) -> list[Project]:
    filters = {"instance_id": instance_id, "deleted_at": None}
    return await DatabaseUtils.get_by_filter(db, Project, filters)


async def project_exists_by_name(db: AsyncSession, project_name: str) -> bool:
    return await DatabaseUtils.exists(db, Project, "project_name", project_name)


async def user_in_project(
    db: AsyncSession, user_id: int, project_id: int
) -> UserToProject | None:
    """Check if a user is already in a project."""
    filters = {"user_id": user_id, "project_id": project_id}
    return await DatabaseUtils.get_one_by_filter(db, UserToProject, filters)


async def add_user_to_project(
    db: AsyncSession,
    user_id: int,
    project_id: int,
    permission: ProjectPermission = ProjectPermission.READ,
    *,
    commit: bool = True,
) -> UserToProject:
    """Add a user to a project with specified permission."""
    # Check if user is already in the project
    existing_membership = await user_in_project(db, user_id, project_id)
    if existing_membership:
        logger.warning(
            "User is already in project",
            extra={
                "user_id": user_id,
                "project_id": project_id,
                "existing_permission": existing_membership.permission,
                "requested_permission": permission,
            },
        )
        raise ValueError("User is already a member of this project")

    user_to_project = UserToProject(
        user_id=user_id,
        project_id=project_id,
        permission=permission,
    )
    db.add(user_to_project)
    if commit:
        await db.commit()
    else:
        await db.flush()
    await db.refresh(user_to_project)
    return user_to_project


async def list_projects_by_user(
    db: AsyncSession, user_id: int, instance_id: int
) -> list[Project]:
    """Get all projects that a user has access to in a given instance."""
    # Join Project with UserToProject to get only projects the user has access to
    stmt = (
        select(Project)
        .join(UserToProject, Project.project_id == UserToProject.project_id)
        .where(UserToProject.user_id == user_id, Project.instance_id == instance_id)
        .where(Project.deleted_at.is_(None))
    )

    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_user_project_permission(
    db: AsyncSession,
    user_id: int,
    project_id: int,
    permission: ProjectPermission,
) -> UserToProject | None:
    """Update a user's permission for a project."""
    # Check if user is in the project
    existing_membership = await user_in_project(db, user_id, project_id)
    if not existing_membership:
        logger.warning(
            "User is not in project",
            extra={
                "user_id": user_id,
                "project_id": project_id,
            },
        )
        return None

    # Update permission
    existing_membership.permission = permission
    await db.commit()
    await db.refresh(existing_membership)
    return existing_membership


async def get_project_admins_and_owners(db: AsyncSession, project_id: int) -> list[int]:
    """Get all user IDs with ADMIN or OWNER permissions for a project."""
    query = select(UserToProject.user_id).where(
        UserToProject.project_id == project_id,
        UserToProject.permission.in_(
            [ProjectPermission.ADMIN, ProjectPermission.OWNER]
        ),
    )
    result = await db.execute(query)
    return list(result.scalars().all())
