from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import OrderStatus

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    sku: str
    unit_price: float
    quantity: int
    total_price: float
    fulfillment_status: str

    class Config:
        from_attributes = True

class OrderStatusHistoryOut(BaseModel):
    id: int
    from_status: Optional[OrderStatus] = None
    to_status: OrderStatus
    comment: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class OrderOut(BaseModel):
    id: int
    order_number: str
    user_id: int
    shipping_address_id: Optional[int] = None
    billing_address_id: Optional[int] = None
    shipping_method_id: Optional[int] = None
    subtotal_amount: float
    discount_amount: float
    tax_amount: float
    shipping_amount: float
    total_amount: float
    status: OrderStatus
    coupon_code: Optional[str] = None
    notes: Optional[str] = None
    items: List[OrderItemOut] = []
    status_history: List[OrderStatusHistoryOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
