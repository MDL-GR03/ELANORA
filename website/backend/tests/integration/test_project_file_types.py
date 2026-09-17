"""Project file types as administrators see them after each change."""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.file_type import preview_importable_file_types
from app.model.instance import Instance
from app.model.project import Project
from app.service.file_type import FileTypeService


async def _projects(session: AsyncSession) -> tuple[Project, Project]:
    instance = Instance(
        instance_name="File Type Lab",
        institution_name="File Type Institute",
        contact_email="admin@filetypes.example",
        domain="filetypes.example",
        timezone="UTC",
    )
    session.add(instance)
    await session.flush()
    source = Project(
        project_name="source", project_path="source", instance_id=instance.instance_id
    )
    target = Project(
        project_name="target", project_path="target", instance_id=instance.instance_id
    )
    session.add_all([source, target])
    await session.commit()
    return source, target


@pytest.mark.asyncio
async def test_a_renamed_file_type_is_returned_with_its_new_name(
    session: AsyncSession,
) -> None:
    project, _ = await _projects(session)
    created = await FileTypeService.create_file_type_for_project(
        session, "ELAN", "eaf", project.project_id
    )

    renamed = await FileTypeService.update_project_file_type(
        session, project.project_id, created.id, {"name": "Annotations"}
    )

    assert renamed.name == "Annotations"
    assert renamed.file_type.extension == "eaf"


@pytest.mark.asyncio
async def test_import_preview_lists_source_types_and_marks_existing_ones(
    session: AsyncSession,
) -> None:
    source, target = await _projects(session)
    await FileTypeService.create_file_type_for_project(
        session, "ELAN", "eaf", source.project_id
    )
    await FileTypeService.create_file_type_for_project(
        session, "Video", "mp4", source.project_id
    )
    await FileTypeService.create_file_type_for_project(
        session, "ELAN", "eaf", target.project_id
    )

    preview = await preview_importable_file_types(
        source.project_id, target.project_id, db=session
    )

    assert sorted(
        (item.name, item.extension, item.exists_in_target) for item in preview
    ) == [
        ("ELAN", "eaf", True),
        ("Video", "mp4", False),
    ]
