"""Service for address-related operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.address import Address
from app.model.city import City
from app.model.country import Country
from app.schema.requests.user import AddressRequest


class AddressService:
    """Service class for address operations."""

    @staticmethod
    async def _city_for(db: AsyncSession, address_data: AddressRequest) -> City:
        """Find the city an address names, creating it and its country if new.

        Cities are matched without regard to case or surrounding spaces, so
        "Lyon" and " lyon" are the same place.
        """
        country = await db.scalar(
            select(Country).where(Country.country_code == address_data.country_code)
        )
        if country is None:
            country = Country(
                country_code=address_data.country_code,
                country_name=address_data.country_name,
            )
            db.add(country)
            await db.flush()

        city_name = address_data.city_name.strip()
        city = await db.scalar(
            select(City).where(
                City.country_id == country.country_id,
                func.lower(func.trim(City.city_name)) == city_name.lower(),
            )
        )
        if city is None:
            city = City(city_name=city_name, country_id=country.country_id)
            db.add(city)
            await db.flush()
        return city

    @staticmethod
    def _apply(address: Address, address_data: AddressRequest, city: City) -> None:
        address.street_number = address_data.street_number
        address.street_name = address_data.street_name
        address.city_id = city.city_id
        address.postal_code = address_data.postal_code
        address.address_line_2 = address_data.address_line_2

    @classmethod
    async def create_address(
        cls,
        db: AsyncSession,
        address_data: AddressRequest,
        *,
        commit: bool = True,
    ) -> Address:
        """Create a new address, creating its city and country when new."""
        try:
            address = Address()
            cls._apply(address, address_data, await cls._city_for(db, address_data))
            db.add(address)
            await db.flush()
            await db.refresh(address)
            if commit:
                await db.commit()
            return address
        except Exception:
            await db.rollback()
            raise

    @classmethod
    async def update_address(
        cls,
        db: AsyncSession,
        address: Address,
        address_data: AddressRequest,
    ) -> Address:
        """Update an existing address."""
        try:
            cls._apply(address, address_data, await cls._city_for(db, address_data))
            await db.flush()
            await db.refresh(address)
            await db.commit()
            return address
        except Exception:
            await db.rollback()
            raise
