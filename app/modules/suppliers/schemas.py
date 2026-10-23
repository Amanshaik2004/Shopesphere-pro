from typing import Optional
from pydantic import BaseModel, EmailStr

class SupplierCreate(BaseModel):
    name: str
    contact_person: str
    email: EmailStr
    phone: str
    address: str
    tax_id: Optional[str] = None
    status: str = "ACTIVE"

class SupplierUpdate(BaseModel):
    name: Optional[str] = None
    contact_person: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    tax_id: Optional[str] = None
    status: Optional[str] = None

class SupplierOut(BaseModel):
    id: int
    name: str
    contact_person: str
    email: str
    phone: str
    address: str
    tax_id: Optional[str] = None
    status: str

    class Config:
        from_attributes = True
