from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import DiscountType

class CouponCreate(BaseModel):
    code: str
    discount_type: DiscountType
    discount_value: float = Field(gt=0)
    min_purchase_amount: float = 0.0
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    valid_from: datetime
    valid_to: datetime
    is_active: bool = True

class CouponUpdate(BaseModel):
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    min_purchase_amount: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: Optional[bool] = None

class CouponOut(BaseModel):
    id: int
    code: str
    discount_type: DiscountType
    discount_value: float
    min_purchase_amount: float
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    usage_count: int
    valid_from: datetime
    valid_to: datetime
    is_active: bool

    class Config:
        from_attributes = True
