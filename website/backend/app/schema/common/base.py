from pydantic import BaseModel, ConfigDict


class CustomBaseModel(BaseModel):
    """Base model that forbids extra fields not defined in the schema and supports ORM serialization."""

    model_config = ConfigDict(
        extra="forbid",
        from_attributes=True,
        populate_by_name=True,
    )
