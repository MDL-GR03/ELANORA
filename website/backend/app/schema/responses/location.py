"""Location-related response schemas."""

from pydantic import BaseModel, ConfigDict


class CountryResponse(BaseModel):
    """Response schema for country information."""

    country_id: int
    country_code: str
    country_name: str

    model_config = ConfigDict(from_attributes=True)


class CityResponse(BaseModel):
    """Response schema for city information."""

    city_id: int
    city_name: str
    country_id: int
    region_state: str | None = None
    country: CountryResponse | None = None

    model_config = ConfigDict(from_attributes=True)
