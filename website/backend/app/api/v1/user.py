from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import ElanoraError, ErrorCode
from app.core.password_policy import password_policy_violation
from app.crud.user import get_all_active_users, get_all_users
from app.dependency.database import get_db_dep
from app.dependency.user import get_admin_dep, get_user_dep
from app.model.address import Address
from app.model.city import City
from app.model.user import User
from app.schema.requests.user import (
    AccountStatusRequest,
    AddressRequest,
    ChangePasswordRequest,
    ProfileUpdateRequest,
)
from app.schema.responses.user import (
    AddressResponse,
    CityResponse,
    ProfileUpdateResponse,
    UserListResponse,
    UserProfileResponse,
    UserResponse,
)
from app.service import user_account_status, user_passwords, user_profile
from app.service.address import AddressService
from app.service.user_errors import (
    AccountNotFoundError,
    AdministratorNoLongerActiveError,
    LastAdministratorError,
    RedundantAccountStatusError,
    SelfAccountStatusError,
)
from app.utils.database import DatabaseUtils

router = APIRouter()

# Account lifecycle refusals are published as fixed, reviewable messages so
# no internal exception text can reach an institution administrator.


@router.get("/me", response_model=UserResponse)
async def get_current_user_data(
    user: User = get_user_dep,
) -> UserResponse:
    """Retrieve the current user object."""
    return UserResponse(
        user_id=user.user_id,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        is_active=user.is_active,
        is_verified_account=user.is_verified_account,
        created_at=user.created_at,
    )


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_current_user_profile(
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> UserProfileResponse:
    """Retrieve the current user's complete profile including address."""
    # Fetch user with address, city, and country relationships preloaded
    user_with_address = await DatabaseUtils.get_by_id(
        db,
        User,
        "user_id",
        user.user_id,
        options=[
            selectinload(User.address)
            .selectinload(Address.city)
            .selectinload(City.country)
        ],
    )

    address_data = None
    if user_with_address and user_with_address.address:
        city_obj = user_with_address.address.city
        city_response = None
        if city_obj:
            city_response = CityResponse(
                city_id=city_obj.city_id,
                name=city_obj.city_name,
                country=city_obj.country.country_name if city_obj.country else None,
            )
        address_data = AddressResponse(
            address_id=user_with_address.address.address_id,
            street_number=user_with_address.address.street_number,
            street_name=user_with_address.address.street_name,
            city_id=user_with_address.address.city_id,
            postal_code=user_with_address.address.postal_code,
            address_line_2=user_with_address.address.address_line_2,
            created_at=user_with_address.address.created_at,
            updated_at=user_with_address.address.updated_at,
            city=city_response,
        )

    # Use current user data or fetched user data
    target_user = user_with_address or user

    return UserProfileResponse(
        user_id=target_user.user_id,
        username=target_user.username,
        email=target_user.email,
        first_name=target_user.first_name,
        last_name=target_user.last_name,
        phone_number=target_user.phone_number,
        affiliation=target_user.affiliation,
        department=target_user.department,
        role=target_user.role.value,
        is_active=target_user.is_active,
        is_verified_account=target_user.is_verified_account,
        created_at=target_user.created_at,
        updated_at=target_user.updated_at,
        last_login=target_user.last_login,
        address=address_data,
    )


@router.put("/me/profile", response_model=ProfileUpdateResponse)
async def update_current_user_profile(
    profile_data: ProfileUpdateRequest,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> ProfileUpdateResponse:
    """Update the current user's profile."""
    try:
        updated_fields = await user_profile.update_profile(db, user, profile_data)
    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.PROFILE_UPDATE_FAILED) from e
    return ProfileUpdateResponse(
        message="Profile updated successfully",
        updated_fields=updated_fields,
        address_updated=False,
    )


@router.put("/me/address", response_model=AddressResponse)
async def update_current_user_address(
    address_data: AddressRequest,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> AddressResponse:
    """Update the current user's address."""
    try:
        # Get user with current address
        user_with_address = await DatabaseUtils.get_by_id(
            db,
            User,
            "user_id",
            user.user_id,
            options=[
                selectinload(User.address)
                .selectinload(Address.city)
                .selectinload(City.country),
            ],
        )

        if user_with_address is None:
            raise ElanoraError(ErrorCode.ACCOUNT_NOT_FOUND)
        if user_with_address.address:
            # Update existing address
            updated_address = await AddressService.update_address(
                db, user_with_address.address, address_data
            )
        else:
            # Create new address
            updated_address = await AddressService.create_address(db, address_data)
            # Update user with new address
            user_with_address.address_id = updated_address.address_id
            await db.flush()
            await db.commit()

        # Reload the address with city and country relationships
        updated_address_with_relations = await DatabaseUtils.get_by_id(
            db,
            Address,
            "address_id",
            updated_address.address_id,
            options=[
                selectinload(Address.city).selectinload(City.country),
            ],
        )

        if updated_address_with_relations is None:
            raise ElanoraError(ErrorCode.ADDRESS_UPDATE_FAILED)
        city_obj = updated_address_with_relations.city

        return AddressResponse(
            address_id=updated_address_with_relations.address_id,
            street_number=updated_address_with_relations.street_number,
            street_name=updated_address_with_relations.street_name,
            city_id=updated_address_with_relations.city_id,
            city=CityResponse(
                city_id=city_obj.city_id,
                name=city_obj.city_name,
                country=city_obj.country.country_name,
            ),
            postal_code=updated_address_with_relations.postal_code,
            address_line_2=updated_address_with_relations.address_line_2,
            created_at=updated_address_with_relations.created_at,
            updated_at=updated_address_with_relations.updated_at,
        )

    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.ADDRESS_UPDATE_FAILED) from e


@router.get("/active", response_model=UserListResponse)
async def get_active_users(
    user: User = get_admin_dep,
    db: AsyncSession = get_db_dep,
) -> UserListResponse:
    """Get all active institution users for administrator member management."""
    users = await get_all_active_users(db, user.instance_id)

    return UserListResponse(
        users=[
            UserResponse(
                user_id=u.user_id,
                username=u.username,
                email=u.email,
                first_name=u.first_name,
                last_name=u.last_name,
                role=u.role.value,
                is_active=u.is_active,
                is_verified_account=u.is_verified_account,
                created_at=u.created_at,
            )
            for u in users
        ]
    )


@router.get("/admin/accounts", response_model=UserListResponse)
async def get_institution_accounts(
    user: User = get_admin_dep,
    db: AsyncSession = get_db_dep,
) -> UserListResponse:
    """List active and suspended accounts in the administrator's institution."""
    users = await get_all_users(db, user.instance_id)
    return UserListResponse(
        users=[UserResponse.model_validate(account) for account in users]
    )


@router.patch("/admin/accounts/{user_id}/status", response_model=UserResponse)
async def set_institution_account_status(
    user_id: int,
    request: AccountStatusRequest,
    user: User = get_admin_dep,
    db: AsyncSession = get_db_dep,
) -> UserResponse:
    """Suspend or restore an account without deleting its research history."""
    try:
        updated = await user_account_status.set_account_active(
            db,
            actor=user,
            target_user_id=user_id,
            is_active=request.is_active,
            reason=request.reason,
        )
    except AdministratorNoLongerActiveError as error:
        raise ElanoraError(ErrorCode.ADMINISTRATOR_INACTIVE) from error
    except AccountNotFoundError as error:
        raise ElanoraError(ErrorCode.ACCOUNT_NOT_FOUND) from error
    except SelfAccountStatusError as error:
        raise ElanoraError(ErrorCode.SELF_STATUS_CHANGE_REFUSED) from error
    except LastAdministratorError as error:
        raise ElanoraError(ErrorCode.LAST_ADMINISTRATOR_REFUSED) from error
    except RedundantAccountStatusError as error:
        raise ElanoraError(ErrorCode.ACCOUNT_STATUS_UNCHANGED) from error
    return UserResponse.model_validate(updated)


@router.put("/me/password")
async def change_user_password(
    request: ChangePasswordRequest,
    user: User = get_user_dep,
    db: AsyncSession = get_db_dep,
) -> dict[str, str]:
    """Change the current user's password."""
    refusal = password_policy_violation(
        request.new_password,
        (user.username, user.email, user.first_name, user.last_name),
    )
    if refusal:
        raise ElanoraError(ErrorCode(f"password_{refusal}"))
    try:
        await user_passwords.change_password(
            db=db,
            user=user,
            current_password=request.current_password,
            new_password=request.new_password,
        )
    except ElanoraError:
        raise
    except Exception as e:
        raise ElanoraError(ErrorCode.PASSWORD_CHANGE_FAILED) from e
    return {"message": "Password changed successfully"}
