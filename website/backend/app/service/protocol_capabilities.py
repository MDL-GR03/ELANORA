"""Delegating protocol management inside a project."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.audit_event import AuditEvent
from app.model.enums import (
    ProjectCapability,
)
from app.model.project import Project
from app.service.protocol_errors import (
    ProtocolConflictError,
)


async def grant_protocol_manager(
    db: AsyncSession, *, project: Project, user_id: int, actor_user_id: int
) -> ProjectCapabilityGrant:
    """Delegate protocol management only to an existing project member."""
    membership = await db.get(UserToProject, (project.project_id, user_id))
    if membership is None:
        raise ProtocolConflictError("Protocol managers must be project members")
    grant = await db.get(
        ProjectCapabilityGrant,
        (project.project_id, user_id, ProjectCapability.MANAGE_PROTOCOLS),
    )
    if grant is None:
        grant = ProjectCapabilityGrant(
            project_id=project.project_id,
            user_id=user_id,
            capability=ProjectCapability.MANAGE_PROTOCOLS,
        )
        db.add(grant)
        db.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                project_id=project.project_id,
                action="project.capability.granted",
                resource_type="user",
                resource_id=str(user_id),
                details={"capability": ProjectCapability.MANAGE_PROTOCOLS.value},
            )
        )
        await db.flush()
    return grant


async def revoke_protocol_manager(
    db: AsyncSession, *, project: Project, user_id: int, actor_user_id: int
) -> None:
    """Revoke delegated protocol management without changing membership."""
    grant = await db.get(
        ProjectCapabilityGrant,
        (project.project_id, user_id, ProjectCapability.MANAGE_PROTOCOLS),
    )
    if grant is not None:
        await db.delete(grant)
        db.add(
            AuditEvent(
                actor_user_id=actor_user_id,
                project_id=project.project_id,
                action="project.capability.revoked",
                resource_type="user",
                resource_id=str(user_id),
                details={"capability": ProjectCapability.MANAGE_PROTOCOLS.value},
            )
        )
        await db.flush()
