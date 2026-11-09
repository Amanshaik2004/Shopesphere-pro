from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import DiscountType, PromotionType

class PromotionCreate(BaseModel):
    name: str
    description: Optional[str] = None
    promotion_type: PromotionType = PromotionType.PRODUCT
    discount_type: DiscountType
    discount_value: float = Field(gt=0)
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    customer_segment_id: Optional[int] = None
    min_cart_value: float = 0.0
    max_discount_amount: Optional[float] = None
    priority: int = 0
    can_stack: bool = True
    usage_limit: Optional[int] = None
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class PromotionUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    promotion_type: Optional[PromotionType] = None
    discount_type: Optional[DiscountType] = None
    discount_value: Optional[float] = None
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    customer_segment_id: Optional[int] = None
    min_cart_value: Optional[float] = None
    max_discount_amount: Optional[float] = None
    priority: Optional[int] = None
    can_stack: Optional[bool] = None
    usage_limit: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_active: Optional[bool] = None

class PromotionOut(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    promotion_type: PromotionType
    discount_type: DiscountType
    discount_value: float
    category_id: Optional[int] = None
    product_id: Optional[int] = None
    customer_segment_id: Optional[int] = None
    min_cart_value: float
    max_discount_amount: Optional[float] = None
    priority: int
    can_stack: bool
    usage_limit: Optional[int] = None
    usage_count: int
    start_date: datetime
    end_date: datetime
    is_active: bool

    class Config:
        from_attributes = True
