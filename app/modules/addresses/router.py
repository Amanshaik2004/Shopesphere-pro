from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import Address, User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError, ForbiddenError
from app.modules.addresses.schemas import AddressCreate, AddressUpdate, AddressOut

router = APIRouter(prefix="/addresses", tags=["Module 05: Address Management"])

@router.post("", response_model=ResponseSchema[AddressOut])
def create_address(
    data: AddressCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if data.is_default:
        # unset previous default addresses for this user
        db.query(Address).filter(Address.user_id == current_user.id).update({"is_default": False})

    address = Address(
        user_id=current_user.id,
        address_type=data.address_type,
        full_name=data.full_name,
        phone=data.phone,
        street_address=data.street_address,
        city=data.city,
        state=data.state,
        postal_code=data.postal_code,
        country=data.country,
        is_default=data.is_default
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return ResponseSchema(message="Address added successfully", data=AddressOut.model_validate(address))

@router.get("", response_model=ResponseSchema[List[AddressOut]])
def get_my_addresses(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    addresses = db.query(Address).filter(Address.user_id == current_user.id).all()
    return ResponseSchema(data=[AddressOut.model_validate(a) for a in addresses])

@router.get("/{address_id}", response_model=ResponseSchema[AddressOut])
def get_address_by_id(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(Address).filter(Address.id == address_id).first()
    if not address:
        raise NotFoundError("Address not found")
    if address.user_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise ForbiddenError("You do not have permission to view this address")
    return ResponseSchema(data=AddressOut.model_validate(address))

@router.put("/{address_id}", response_model=ResponseSchema[AddressOut])
def update_address(
    address_id: int,
    data: AddressUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(Address).filter(Address.id == address_id).first()
    if not address:
        raise NotFoundError("Address not found")
    if address.user_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise ForbiddenError("You do not have permission to modify this address")

    if data.is_default:
        db.query(Address).filter(Address.user_id == address.user_id).update({"is_default": False})

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(address, key, value)

    db.commit()
    db.refresh(address)
    return ResponseSchema(message="Address updated successfully", data=AddressOut.model_validate(address))

@router.delete("/{address_id}", response_model=ResponseSchema[MessageResponse])
def delete_address(
    address_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    address = db.query(Address).filter(Address.id == address_id).first()
    if not address:
        raise NotFoundError("Address not found")
    if address.user_id != current_user.id and current_user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
        raise ForbiddenError("You do not have permission to delete this address")

    db.delete(address)
    db.commit()
    return ResponseSchema(message="Address deleted successfully", data=MessageResponse(message="Address removed"))
