from pydantic import BaseModel


class EffectiveNamingStandardOut(BaseModel):
    id: int
    project_id: int
    project_file_type_id: int
    naming_standard_id: int
    location_id: int


class NamingStandardLocationOut(BaseModel):
    id: int
    label: str


class GetNamingStandardLocationsResponse(BaseModel):
    locations: list[NamingStandardLocationOut]


class EffectiveNamingStandardResponse(BaseModel):
    success: bool
    effective_standard: EffectiveNamingStandardOut


class UnassignEffectiveNamingStandardResponse(BaseModel):
    success: bool


class GetEffectiveStandardsResponse(BaseModel):
    effective_standards: list[EffectiveNamingStandardOut]
