from uuid import UUID

from pydantic import BaseModel


class InstanceResponse(BaseModel):
    installation_id: UUID
    instance_name: str
    institution_name: str
    contact_email: str
    domain: str
    timezone: str
    default_language: str
    primary_color: str
    secondary_color: str
    accent_color: str
    logo_url: str | None = None
    max_file_size_mb: float
    max_users: int
