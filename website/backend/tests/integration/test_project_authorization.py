import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.dependency.project_access import (
    ProjectCapabilityGuard,
    ProjectGuard,
)
from app.model.association import ProjectCapabilityGrant, UserToProject
from app.model.enums import ProjectCapability, ProjectPermission, UserRole
from app.model.instance import Instance
from app.model.project import Project
from app.model.user import User


def _instance(name: str) -> Instance:
    return Instance(
        instance_name=name,
        institution_name=name,
        contact_email=f"admin@{name.lower()}.example",
        domain=f"{name.lower()}.example",
        timezone="UTC",
    )


def _user(username: str, instance: Instance, role: UserRole = UserRole.PUBLIC) -> User:
    return User(
        username=username,
        email=f"{username}@example.org",
        hashed_password="unused-test-value",  # noqa: S106 - inert fixture
        first_name=username,
        last_name="Researcher",
        affiliation=instance.institution_name,
        department="Linguistics",
        activation_code="fixture",
        instance=instance,
        role=role,
    )


def _request(project_id: int) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": f"/projects/{project_id}",
            "headers": [],
            "path_params": {"project_id": str(project_id)},
        }
    )


@pytest.mark.asyncio
async def test_project_guard_enforces_membership_and_permission_boundaries(
    session: AsyncSession,
) -> None:
    institution = _instance("First")
    reader = _user("reader", institution)
    outsider = _user("outsider", institution)
    project = Project(
        project_name="Shared corpus",
        description="Authorization fixture",
        project_path="shared-corpus",
        instance=institution,
    )
    session.add_all([institution, reader, outsider, project])
    await session.flush()
    session.add(
        UserToProject(
            user_id=reader.user_id,
            project_id=project.project_id,
            permission=ProjectPermission.READ,
        )
    )
    await session.flush()

    access = await ProjectGuard(ProjectPermission.READ)(
        _request(project.project_id), session, reader
    )
    assert access.project.project_id == project.project_id
    assert access.permission == ProjectPermission.READ

    with pytest.raises(HTTPException) as insufficient:
        await ProjectGuard(ProjectPermission.WRITE)(
            _request(project.project_id), session, reader
        )
    assert insufficient.value.status_code == 403

    with pytest.raises(HTTPException) as hidden_nonmember_project:
        await ProjectGuard(ProjectPermission.READ)(
            _request(project.project_id), session, outsider
        )
    assert hidden_nonmember_project.value.status_code == 404


@pytest.mark.asyncio
async def test_protocol_capability_is_independent_from_write_and_admin_access(
    session: AsyncSession,
) -> None:
    institution = _instance("Capability")
    researcher = _user("protocol-manager", institution)
    project = Project(
        project_name="Governed project",
        description="Capability fixture",
        project_path="governed-project",
        instance=institution,
    )
    session.add_all([institution, researcher, project])
    await session.flush()
    session.add(
        UserToProject(
            user_id=researcher.user_id,
            project_id=project.project_id,
            permission=ProjectPermission.READ,
        )
    )
    await session.flush()
    guard = ProjectCapabilityGuard(ProjectCapability.MANAGE_PROTOCOLS)

    with pytest.raises(HTTPException) as missing_capability:
        await guard(_request(project.project_id), session, researcher)
    assert missing_capability.value.status_code == 403

    session.add(
        ProjectCapabilityGrant(
            project_id=project.project_id,
            user_id=researcher.user_id,
            capability=ProjectCapability.MANAGE_PROTOCOLS,
        )
    )
    await session.flush()

    access = await guard(_request(project.project_id), session, researcher)
    assert access.permission == ProjectPermission.READ
    with pytest.raises(HTTPException) as still_not_writer:
        await ProjectGuard(ProjectPermission.WRITE)(
            _request(project.project_id), session, researcher
        )
    assert still_not_writer.value.status_code == 403
