from datetime import datetime
from pydantic import BaseModel
from app.common.enums import ShipmentStatus

class TrackingEventCreate(BaseModel):
    shipment_id: int
    status: ShipmentStatus
    location: str
    description: str

class TrackingEventOut(BaseModel):
    id: int
    shipment_id: int
    status: ShipmentStatus
    location: str
    description: str
    event_time: datetime

    class Config:
        from_attributes = True
