from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.instance import Instance
from app.model.project import Project
from app.model.project_integrity import ProjectIntegrityStatus
from app.service.operations import operations_status


@pytest.mark.asyncio
async def test_operations_status_counts_unhealthy_and_unscanned_projects(
    session: AsyncSession,
) -> None:
    institution = Instance(
        instance_name="operations",
        institution_name="Operations Institute",
        contact_email="operations@example.org",
        domain="example.org",
        timezone="UTC",
    )
    healthy = Project(
        project_name="healthy",
        project_path="healthy",
        instance=institution,
    )
    unhealthy = Project(
        project_name="unhealthy",
        project_path="unhealthy",
        instance=institution,
    )
    unscanned = Project(
        project_name="unscanned",
        project_path="unscanned",
        instance=institution,
    )
    session.add_all([institution, healthy, unhealthy, unscanned])
    await session.flush()
    checked_at = datetime.now(UTC)
    session.add_all(
        [
            ProjectIntegrityStatus(
                project_id=healthy.project_id,
                status="healthy",
                details={},
                last_checked_at=checked_at,
            ),
            ProjectIntegrityStatus(
                project_id=unhealthy.project_id,
                status="corrupt",
                details={"missing_files": ["session.eaf"]},
                first_detected_at=checked_at,
                last_checked_at=checked_at,
            ),
        ]
    )
    await session.flush()

    result = await operations_status(session)

    assert result.integrity.total_projects == 3
    assert result.integrity.scanned_projects == 2
    assert result.integrity.healthy_projects == 1
    assert result.integrity.unhealthy_projects == 1
    assert result.integrity.unscanned_projects == 1
    assert result.integrity.latest_check_at == checked_at
    assert result.publication_queue.queued == 0
    assert result.publication_queue.running == 0
    assert result.publication_queue.review_needed == 0
    assert result.publication_queue.failed == 0
