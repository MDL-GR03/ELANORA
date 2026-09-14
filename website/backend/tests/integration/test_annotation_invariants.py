"""Database enforcement for annotation ownership and time ranges."""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.annotation import Annotation
from app.model.annotation_value import AnnotationValue
from app.model.elan_file import ElanFile
from app.model.file_content import FileContent
from app.model.instance import Instance
from app.model.project import Project
from app.model.tier import Tier


async def _annotation_fixture(
    session: AsyncSession,
) -> tuple[ElanFile, ElanFile, Tier, Tier, AnnotationValue]:
    instance = Instance(
        instance_name="Annotation constraints",
        institution_name="Research institute",
        contact_email="admin@example.org",
        domain="example.org",
        timezone="UTC",
    )
    session.add(instance)
    await session.flush()
    project = Project(
        project_name="Corpus",
        project_path="annotation-constraints",
        instance_id=instance.instance_id,
    )
    first_content = FileContent(
        filename="first.eaf",
        file_size=1,
        content_hash="a" * 64,
    )
    second_content = FileContent(
        filename="second.eaf",
        file_size=1,
        content_hash="b" * 64,
    )
    session.add_all([project, first_content, second_content])
    await session.flush()
    first_file = ElanFile(
        content_id=first_content.content_id,
        project_id=project.project_id,
        filename="first.eaf",
        file_path="Corpus/elan_files/first.eaf",
        last_modified=datetime.now(),
    )
    second_file = ElanFile(
        content_id=second_content.content_id,
        project_id=project.project_id,
        filename="second.eaf",
        file_path="Corpus/elan_files/second.eaf",
        last_modified=datetime.now(),
    )
    session.add_all([first_file, second_file])
    await session.flush()
    first_tier = Tier(
        tier_name="utterance",
        linguistic_type_ref="default-lt",
        elan_id=first_file.elan_id,
    )
    second_tier = Tier(
        tier_name="utterance",
        linguistic_type_ref="default-lt",
        elan_id=second_file.elan_id,
    )
    value = AnnotationValue(annotation_value="Test annotation")
    session.add_all([first_tier, second_tier, value])
    await session.flush()
    return first_file, second_file, first_tier, second_tier, value


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("start_time", "end_time"),
    [
        (Decimal("-0.001"), Decimal("1.000")),
        (Decimal("0.000"), Decimal("-0.001")),
        (Decimal("2.000"), Decimal("1.999")),
    ],
)
async def test_database_rejects_invalid_annotation_times(
    session: AsyncSession,
    start_time: Decimal,
    end_time: Decimal,
) -> None:
    first_file, _, first_tier, _, value = await _annotation_fixture(session)
    session.add(
        Annotation(
            annotation_id="invalid-time",
            elan_id=first_file.elan_id,
            value_id=value.value_id,
            annotation_kind="alignable",
            start_time=start_time,
            end_time=end_time,
            tier_id=first_tier.tier_id,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_database_rejects_a_tier_from_another_elan_file(
    session: AsyncSession,
) -> None:
    first_file, _, _, second_tier, value = await _annotation_fixture(session)
    session.add(
        Annotation(
            annotation_id="wrong-tier-owner",
            elan_id=first_file.elan_id,
            value_id=value.value_id,
            annotation_kind="reference",
            tier_id=second_tier.tier_id,
        )
    )

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_database_accepts_valid_and_unaligned_annotations(
    session: AsyncSession,
) -> None:
    first_file, _, first_tier, _, value = await _annotation_fixture(session)
    session.add_all(
        [
            Annotation(
                annotation_id="valid-time",
                elan_id=first_file.elan_id,
                value_id=value.value_id,
                annotation_kind="alignable",
                start_time=Decimal("0.000"),
                end_time=Decimal("1.250"),
                tier_id=first_tier.tier_id,
            ),
            Annotation(
                annotation_id="unaligned-reference",
                elan_id=first_file.elan_id,
                value_id=value.value_id,
                annotation_kind="reference",
                tier_id=first_tier.tier_id,
            ),
        ]
    )

    await session.flush()
