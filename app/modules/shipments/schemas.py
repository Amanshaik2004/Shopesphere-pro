from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import ShipmentStatus

class ShipmentCreate(BaseModel):
    order_id: int
    carrier: str = "Standard Express"

class ShipmentOut(BaseModel):
    id: int
    order_id: int
    carrier: str
    tracking_number: str
    status: ShipmentStatus
    shipped_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    shipping_label_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
