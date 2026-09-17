from app.schema.common.base import CustomBaseModel


class NamingComponentResponse(CustomBaseModel):
    id: int
    name: str
    regex: str
    description: str | None = ""
    order: int
    accepted_values: list[str] | None = None
    project_file_type_id: int


class NamingStandardResponse(CustomBaseModel):
    id: int
    project_id: int
    name: str
    project_file_type_id: int
    file_type_id: int
    file_type_name: str
    pattern: str
    description: str | None = ""
    components: list[NamingComponentResponse]


class NamingStandardSummaryResponse(CustomBaseModel):
    id: int
    project_id: int
    name: str
    project_file_type_id: int
    pattern: str
    description: str | None = ""


class ProjectNamingStandardsResponse(CustomBaseModel):
    component_names: list[str]
    standards: list[NamingStandardResponse]


class ProjectWithStandardsResponse(CustomBaseModel):
    id: int
    name: str


class ImportSelectedStandardsResponse(CustomBaseModel):
    imported_standards: list[NamingStandardResponse]
