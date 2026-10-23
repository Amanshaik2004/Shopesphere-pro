from typing import Optional
from pydantic import BaseModel, Field

class ShippingMethodCreate(BaseModel):
    name: str
    carrier: str
    base_cost: float = Field(ge=0)
    free_shipping_threshold: Optional[float] = None
    estimated_days_min: int = Field(ge=1, default=2)
    estimated_days_max: int = Field(ge=1, default=5)
    is_active: bool = True

class ShippingMethodUpdate(BaseModel):
    name: Optional[str] = None
    carrier: Optional[str] = None
    base_cost: Optional[float] = None
    free_shipping_threshold: Optional[float] = None
    estimated_days_min: Optional[int] = None
    estimated_days_max: Optional[int] = None
    is_active: Optional[bool] = None

class ShippingMethodOut(BaseModel):
    id: int
    name: str
    carrier: str
    base_cost: float
    free_shipping_threshold: Optional[float] = None
    estimated_days_min: int
    estimated_days_max: int
    is_active: bool

    class Config:
        from_attributes = True
