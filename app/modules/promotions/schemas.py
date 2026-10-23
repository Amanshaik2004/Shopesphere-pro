from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import DiscountType

class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float = Field(gt=0)
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class PromotionOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    discount_type: DiscountType
    discount_value: float
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    start_date: datetime
    end_date: datetime
    is_active: bool

    class Config:
        from_attributes = True
