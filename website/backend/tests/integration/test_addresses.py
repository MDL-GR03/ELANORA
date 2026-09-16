"""Addresses reuse the cities and countries already on record."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.city import City
from app.model.country import Country
from app.schema.requests.user import AddressRequest
from app.service.address import AddressService


def _request(**overrides: str | None) -> AddressRequest:
    values: dict[str, str | None] = {
        "street_name": "Rue Garibaldi",
        "street_number": "12",
        "city_name": "Lyon",
        "country_code": "FR",
        "country_name": "France",
        "postal_code": "69003",
        "address_line_2": None,
    }
    values.update(overrides)
    return AddressRequest(**values)


@pytest.mark.asyncio
async def test_creating_an_address_records_its_city_and_country(
    session: AsyncSession,
) -> None:
    address = await AddressService.create_address(session, _request())

    city = await session.get(City, address.city_id)
    assert city is not None and city.city_name == "Lyon"
    country = await session.get(Country, city.country_id)
    assert country is not None and country.country_code == "FR"
    assert address.street_name == "Rue Garibaldi"
    assert address.postal_code == "69003"


@pytest.mark.asyncio
async def test_the_same_city_written_differently_is_not_recorded_twice(
    session: AsyncSession,
) -> None:
    first = await AddressService.create_address(session, _request())
    second = await AddressService.create_address(
        session, _request(city_name="  lyon ", street_name="Cours Lafayette")
    )

    assert second.city_id == first.city_id
    assert await session.scalar(select(func.count()).select_from(City)) == 1
    assert await session.scalar(select(func.count()).select_from(Country)) == 1


@pytest.mark.asyncio
async def test_updating_an_address_moves_it_to_another_city(
    session: AsyncSession,
) -> None:
    address = await AddressService.create_address(session, _request())
    original_city = address.city_id

    updated = await AddressService.update_address(
        session,
        address,
        _request(
            city_name="Bruxelles",
            country_code="BE",
            country_name="Belgium",
            postal_code="1000",
            street_number=None,
        ),
    )

    assert updated.address_id == address.address_id
    assert updated.city_id != original_city
    assert updated.street_number is None
    assert await session.scalar(select(func.count()).select_from(Country)) == 2
