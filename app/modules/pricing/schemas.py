from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class PriceUpdateRequest(BaseModel):
    base_price: float = Field(gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    reason: Optional[str] = "Price updated by product manager"

class PriceHistoryOut(BaseModel):
    id: int
    product_id: int
    old_base_price: float
    new_base_price: float
    old_sale_price: Optional[float] = None
    new_sale_price: Optional[float] = None
    changed_by_user_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class PriceBreakdownItemInput(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(..., gt=0)


class PriceBreakdownRequest(BaseModel):
    items: List[PriceBreakdownItemInput]
    coupon_code: Optional[str] = None
    customer_id: Optional[int] = None
    shipping_method_id: Optional[int] = None


class ItemBreakdownOut(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    sku: str
    quantity: int
    unit_price: float
    item_subtotal: float
    product_discount: float
    category_discount: float
    net_item_price: float


class AppliedPromotionOut(BaseModel):
    promotion_id: Optional[int] = None
    promotion_name: str
    promotion_type: str
    discount_amount: float


class PriceBreakdownResponse(BaseModel):
    items: List[ItemBreakdownOut]
    subtotal_amount: float
    product_promotions_discount: float
    category_promotions_discount: float
    cart_promotions_discount: float
    customer_segment_discount: float
    coupon_discount: float
    total_discount: float
    tax_amount: float
    shipping_amount: float
    total_amount: float
    applied_promotions: List[AppliedPromotionOut] = []
