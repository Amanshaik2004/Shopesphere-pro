from typing import Optional
from pydantic import BaseModel
from app.common.enums import OrderStatus

class OrderStatusUpdate(BaseModel):
    status: OrderStatus
    comment: Optional[str] = None
