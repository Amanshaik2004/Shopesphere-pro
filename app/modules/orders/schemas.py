from typing import Optional, List, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import OrderStatus

class OrderItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    product_name: str
    sku: str
    unit_price: float
    quantity: int
    fulfilled_quantity: int = 0
    cancelled_quantity: int = 0
    total_price: float
    fulfillment_status: str

    class Config:
        from_attributes = True

class OrderStatusHistoryOut(BaseModel):
    id: int
    from_status: Optional[OrderStatus] = None
    to_status: OrderStatus
    actor_role: Optional[str] = None
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


class SplitShipmentItemInput(BaseModel):
    order_item_id: int
    quantity: int = Field(..., gt=0)


class SplitShipmentRequest(BaseModel):
    carrier: str = "Standard Express"
    tracking_number: Optional[str] = None
    items: List[SplitShipmentItemInput]


class SplitShipmentResponse(BaseModel):
    shipment_id: int
    tracking_number: str
    carrier: str
    status: str
    order_id: int
    items: List[dict]


class ItemCancelRequest(BaseModel):
    order_item_id: int
    quantity: int = Field(..., gt=0)
    reason: str


class ItemCancelResponse(BaseModel):
    order_id: int
    order_item_id: int
    cancelled_quantity: int
    refund_amount: float
    order_status: OrderStatus


class BackorderItemRequest(BaseModel):
    order_item_id: int
    notes: Optional[str] = "Item temporarily out of stock"


class OrderTimelineEvent(BaseModel):
    event_type: str
    timestamp: datetime
    description: str
    actor: Optional[str] = None
    details: Optional[dict] = None


class OrderTimelineResponse(BaseModel):
    order_id: int
    order_number: str
    events: List[OrderTimelineEvent]


class ItemFulfillmentDetail(BaseModel):
    order_item_id: int
    product_name: str
    sku: str
    ordered_quantity: int
    fulfilled_quantity: int
    cancelled_quantity: int
    pending_quantity: int
    fulfillment_status: str


class OrderFulfillmentDetailsResponse(BaseModel):
    order_id: int
    order_number: str
    order_status: OrderStatus
    fulfillment_percentage: float
    items: List[ItemFulfillmentDetail]
    shipments_count: int


class AdminOrderUpdateRequest(BaseModel):
    shipping_address_id: Optional[int] = None
    billing_address_id: Optional[int] = None
    notes: Optional[str] = None
    status: Optional[OrderStatus] = None
