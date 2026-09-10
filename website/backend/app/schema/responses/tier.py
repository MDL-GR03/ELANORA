from pydantic import Field

from app.schema.common.base import CustomBaseModel


class TierNode(CustomBaseModel):
    tier_id: int
    tier_name: str
    parent_tier_id: int | None = None
    children: list["TierNode"] = Field(default_factory=list)


TierNode.model_rebuild()


class TierTreeResponse(CustomBaseModel):
    tiers: dict[str, list[TierNode]]


class SectionInfo(CustomBaseModel):
    section_id: int
    name: str


class TierGroupInfo(CustomBaseModel):
    tier_group_id: int
    elan_file_name: str
    section_id: int | None
    tiers: list[TierNode] = Field(default_factory=list)


class SectionsAndGroupsResponse(CustomBaseModel):
    sections: list[SectionInfo]
    tier_groups: list[TierGroupInfo]


class ResearchTopicInfo(CustomBaseModel):
    topic_id: int
    name: str
    description: str | None = None
    tier_names: list[str] = Field(default_factory=list)
    allow_new_tiers: bool = False


class ProjectBaselineTiersInfo(CustomBaseModel):
    tier_names: list[str] = Field(default_factory=list)
