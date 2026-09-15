"""A projected EAF is identified by its filename within a project, not its bytes.

Two sessions annotated from one template can be byte-identical and must both be
storable. Two files with the same name in one project cannot both be current.
"""

from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project


async def _project_and_content(
    session: AsyncSession,
) -> tuple[Project, FileContent]:
    instance = Instance(
        instance_name="File identity",
        institution_name="Research institute",
        contact_email="admin@identity.example",
        domain="identity.example",
        timezone="UTC",
    )
    session.add(instance)
    await session.flush()
    project = Project(
        project_name="Template corpus",
        project_path="file-identity",
        instance_id=instance.instance_id,
    )
    content = FileContent(filename="template.eaf", file_size=1, content_hash="c" * 64)
    session.add_all([project, content])
    await session.flush()
    return project, content


def _file(project: Project, content: FileContent, filename: str) -> ElanFile:
    return ElanFile(
        content_id=content.content_id,
        project_id=project.project_id,
        filename=filename,
        file_path=f"Template corpus/elan_files/{filename}",
        last_modified=datetime.now(),
    )


@pytest.mark.asyncio
async def test_identical_content_may_be_stored_under_different_names(
    session: AsyncSession,
) -> None:
    project, content = await _project_and_content(session)

    session.add_all(
        [
            _file(project, content, "session-01.eaf"),
            _file(project, content, "session-02.eaf"),
        ]
    )
    await session.flush()


@pytest.mark.asyncio
async def test_a_filename_cannot_appear_twice_in_one_project(
    session: AsyncSession,
) -> None:
    project, content = await _project_and_content(session)
    other = FileContent(filename="other.eaf", file_size=2, content_hash="d" * 64)
    session.add(other)
    await session.flush()

    session.add_all(
        [
            _file(project, content, "session-01.eaf"),
            _file(project, other, "session-01.eaf"),
        ]
    )
    with pytest.raises(IntegrityError, match="uq_elan_file_project_filename"):
        await session.flush()
