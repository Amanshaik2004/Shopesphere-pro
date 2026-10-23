from typing import Optional
from pydantic import BaseModel, Field

class TaxRateCreate(BaseModel):
    name: str
    rate_percentage: float = Field(ge=0, le=100)
    country: str = "United States"
    state: Optional[str] = None
    category_id: Optional[int] = None
    is_active: bool = True

class TaxRateUpdate(BaseModel):
    name: Optional[str] = None
    rate_percentage: Optional[float] = None
    country: Optional[str] = None
    state: Optional[str] = None
    category_id: Optional[int] = None
    is_active: Optional[bool] = None

class TaxRateOut(BaseModel):
    id: int
    name: str
    rate_percentage: float
    country: str
    state: Optional[str] = None
    category_id: Optional[int] = None
    is_active: bool

    class Config:
        from_attributes = True
