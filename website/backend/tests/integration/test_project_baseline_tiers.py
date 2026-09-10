import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.tier import (
    get_project_baseline_tiers,
    update_project_baseline_tiers,
)
from app.dependency.project_access import ProjectAccess
from app.model.enums import ProjectPermission, UserRole
from app.model.instance import Instance
from app.model.project import Project
from app.model.user import User
from app.schema.requests.tier import ProjectBaselineTiersRequest


@pytest.mark.asyncio
async def test_project_baseline_tiers_are_replaced_deduplicated_and_persisted(
    session: AsyncSession,
) -> None:
    instance = Instance(
        instance_name="Baseline test",
        institution_name="Research Institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    admin = User(
        username="baseline-admin",
        email="baseline-admin@example.org",
        hashed_password="unused-test-value",  # noqa: S106
        first_name="Baseline",
        last_name="Administrator",
        affiliation="Research Institute",
        department="Linguistics",
        activation_code="fixture",
        role=UserRole.ADMIN,
        instance=instance,
    )
    project = Project(
        project_name="Baseline corpus",
        description="Baseline persistence fixture",
        project_path="baseline-corpus",
        instance=instance,
    )
    session.add_all([instance, admin, project])
    await session.flush()
    access = ProjectAccess(project, admin, ProjectPermission.OWNER)

    saved = await update_project_baseline_tiers(
        project.project_id,
        ProjectBaselineTiersRequest(
            tier_names=["Sign right", " Sign left ", "Sign right"]
        ),
        session,
        access,
    )
    loaded = await get_project_baseline_tiers(project.project_id, session, access)

    assert saved.tier_names == ["Sign left", "Sign right"]
    assert loaded.tier_names == ["Sign left", "Sign right"]
