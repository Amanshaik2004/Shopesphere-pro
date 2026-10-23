from typing import Optional
from pydantic import BaseModel
from app.common.enums import AddressType

class AddressCreate(BaseModel):
    address_type: AddressType = AddressType.SHIPPING
    full_name: str
    phone: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str = "United States"
    is_default: bool = False

class AddressUpdate(BaseModel):
    address_type: Optional[AddressType] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    street_address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    is_default: Optional[bool] = None

class AddressOut(BaseModel):
    id: int
    user_id: int
    address_type: AddressType
    full_name: str
    phone: str
    street_address: str
    city: str
    state: str
    postal_code: str
    country: str
    is_default: bool

    class Config:
        from_attributes = True
