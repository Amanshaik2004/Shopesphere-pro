from typing import Optional
from pydantic import BaseModel

class WarehouseCreate(BaseModel):
    name: str
    code: str
    address: str
    city: str
    state: str
    postal_code: str
    country: str = "United States"
    capacity: int = 10000
    is_active: bool = True
    manager_id: Optional[int] = None

class WarehouseUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None
    manager_id: Optional[int] = None

class WarehouseOut(BaseModel):
    id: int
    name: str
    code: str
    address: str
    city: str
    state: str
    postal_code: str
    country: str
    capacity: int
    is_active: bool
    manager_id: Optional[int] = None

    class Config:
        from_attributes = True
