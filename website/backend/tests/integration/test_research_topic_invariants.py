"""PostgreSQL guarantees for curated research-topic identifiers."""

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.instance import Instance
from app.model.project import Project
from app.model.research_topic import (
    ProjectBaselineTier,
    ResearchTopic,
    ResearchTopicTier,
)


async def _projects(session: AsyncSession) -> tuple[Project, Project]:
    instance = Instance(
        instance_name="Topic constraints",
        institution_name="Research institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    first = Project(
        project_name="First topic corpus",
        project_path="first-topic-corpus",
        instance=instance,
    )
    second = Project(
        project_name="Second topic corpus",
        project_path="second-topic-corpus",
        instance=instance,
    )
    session.add_all([instance, first, second])
    await session.flush()
    return first, second


@pytest.mark.asyncio
async def test_equivalent_topic_names_are_rejected_within_a_project(
    session: AsyncSession,
) -> None:
    project, _ = await _projects(session)
    session.add(ResearchTopic(project_id=project.project_id, name="Prosody analysis"))
    await session.flush()
    session.add(
        ResearchTopic(project_id=project.project_id, name=" PROSODY   analysis ")
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_equivalent_topic_names_remain_valid_in_different_projects(
    session: AsyncSession,
) -> None:
    first, second = await _projects(session)
    session.add_all(
        [
            ResearchTopic(project_id=first.project_id, name="Prosody"),
            ResearchTopic(project_id=second.project_id, name=" prosody "),
        ]
    )

    await session.flush()


@pytest.mark.asyncio
async def test_blank_topic_name_is_rejected(session: AsyncSession) -> None:
    project, _ = await _projects(session)
    session.add(ResearchTopic(project_id=project.project_id, name="   "))

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_blank_topic_tier_name_is_rejected(session: AsyncSession) -> None:
    project, _ = await _projects(session)
    topic = ResearchTopic(project_id=project.project_id, name="Prosody")
    session.add(topic)
    await session.flush()
    session.add(ResearchTopicTier(topic_id=topic.topic_id, tier_name="   "))

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_blank_baseline_tier_name_is_rejected(session: AsyncSession) -> None:
    project, _ = await _projects(session)
    session.add(ProjectBaselineTier(project_id=project.project_id, tier_name="   "))

    with pytest.raises(IntegrityError):
        await session.flush()
