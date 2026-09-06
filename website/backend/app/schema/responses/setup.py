from pydantic import BaseModel

from app.schema.responses.instance import InstanceResponse


class SetupStatusResponse(BaseModel):
    initialized: bool
    setup_token_configured: bool


class SetupInitializeResponse(BaseModel):
    instance: InstanceResponse
    administrator_username: str
