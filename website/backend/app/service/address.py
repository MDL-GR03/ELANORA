"""Service for address-related operations."""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.model.address import Address
from app.model.city import City
from app.model.country import Country
from app.schema.requests.user import AddressRequest


class AddressService:
    """Service class for address operations."""

    @classmethod
    async def create_address(
        cls,
        db: AsyncSession,
        address_data: AddressRequest,
        *,
        commit: bool = True,
    ) -> Address:
        """Create a new address. If city_name is provided, create or get the city, then use its id."""
        try:
            # First, find the country by its code, create if not found
            country_stmt = select(Country).where(
                Country.country_code == address_data.country_code
            )
            country_result = await db.execute(country_stmt)
            country = country_result.scalar_one_or_none()

            if not country:
                # Create the country if it doesn't exist
                country = Country(
                    country_code=address_data.country_code,
                    country_name=address_data.country_name,
                )
                db.add(country)
                await db.flush()
                await db.refresh(country)

            # Find or create city by normalized name and country (case-insensitive, strip)
            normalized_city_name = address_data.city_name.strip().lower()
            stmt = select(City).where(
                (City.country_id == country.country_id)
                & (func.lower(func.trim(City.city_name)) == normalized_city_name)
            )
            result = await db.execute(stmt)
            city = result.scalar_one_or_none()
            if not city:
                city = City(
                    city_name=address_data.city_name.strip(),
                    country_id=country.country_id,
                )
                db.add(city)
                await db.flush()
                await db.refresh(city)

            address = Address(
                street_number=address_data.street_number,
                street_name=address_data.street_name,
                city_id=city.city_id,
                postal_code=address_data.postal_code,
                address_line_2=address_data.address_line_2,
            )

            db.add(address)
            await db.flush()  # Flush to get the address_id
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
            # First, find the country by its code, create if not found
            country_stmt = select(Country).where(
                Country.country_code == address_data.country_code
            )
            country_result = await db.execute(country_stmt)
            country = country_result.scalar_one_or_none()

            if not country:
                # Create the country if it doesn't exist
                country = Country(
                    country_code=address_data.country_code,
                    country_name=address_data.country_name,
                )
                db.add(country)
                await db.flush()
                await db.refresh(country)

            # Find or create city by normalized name and country (case-insensitive, strip)
            normalized_city_name = address_data.city_name.strip().lower()
            stmt = select(City).where(
                (City.country_id == country.country_id)
                & (func.lower(func.trim(City.city_name)) == normalized_city_name)
            )
            result = await db.execute(stmt)
            city = result.scalar_one_or_none()
            if not city:
                city = City(
                    city_name=address_data.city_name.strip(),
                    country_id=country.country_id,
                )
                db.add(city)
                await db.flush()
                await db.refresh(city)

            # Update address fields
            address.street_number = address_data.street_number
            address.street_name = address_data.street_name
            address.city_id = city.city_id
            address.postal_code = address_data.postal_code
            address.address_line_2 = address_data.address_line_2

            await db.flush()
            await db.refresh(address)
            await db.commit()
            return address
        except Exception:
            await db.rollback()
            raise
