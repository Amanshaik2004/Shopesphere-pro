from typing import Optional
from pydantic import BaseModel
from app.modules.orders.schemas import OrderItemOut

class OrderItemFulfillmentUpdate(BaseModel):
    fulfillment_status: str  # PENDING, PACKED, SHIPPED, DELIVERED, CANCELLED
