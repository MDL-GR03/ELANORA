from pydantic import Field

from app.schema.common.base import CustomBaseModel


class TierTreeRequest(CustomBaseModel):
    project_name: str


class CreateSectionRequest(CustomBaseModel):
    project_id: int
    name: str


class RenameSectionRequest(CustomBaseModel):
    section_id: int
    new_name: str


class DeleteSectionRequest(CustomBaseModel):
    section_id: int


class MoveTierGroupRequest(CustomBaseModel):
    tier_group_id: int
    section_id: int | None


class TierSubsetExportRequest(CustomBaseModel):
    """A non-destructive working extract of selected tiers from one EAF."""

    filename: str = Field(min_length=1, max_length=255)
    tier_names: list[str] = Field(min_length=1, max_length=500)
