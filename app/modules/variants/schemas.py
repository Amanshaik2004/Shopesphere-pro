from typing import Optional
from pydantic import BaseModel

class VariantCreate(BaseModel):
    product_id: int
    sku: str
    name: str
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    additional_price: float = 0.0
    is_active: bool = True

class VariantUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    additional_price: Optional[float] = None
    is_active: Optional[bool] = None

class VariantOut(BaseModel):
    id: int
    product_id: int
    sku: str
    name: str
    size: Optional[str] = None
    color: Optional[str] = None
    material: Optional[str] = None
    additional_price: float
    is_active: bool

    class Config:
        from_attributes = True
