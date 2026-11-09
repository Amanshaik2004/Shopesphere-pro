from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import NotificationChannel

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    notification_type: str = "INFO"  # ORDER_STATUS, PAYMENT, REFUND, SHIPMENT, RETURN, SUPPORT
    data: Optional[str] = None
    deduplication_key: Optional[str] = None

class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    channel: NotificationChannel
    notification_type: str
    is_read: bool
    data: Optional[str] = None
    deduplication_key: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class NotificationPreferenceItem(BaseModel):
    channel: NotificationChannel
    event_type: str
    is_enabled: bool

class NotificationPreferencesUpdate(BaseModel):
    preferences: List[NotificationPreferenceItem]

class NotificationPreferenceOut(BaseModel):
    id: int
    channel: NotificationChannel
    event_type: str
    is_enabled: bool

    class Config:
        from_attributes = True

class NotificationDispatchResponse(BaseModel):
    notification_id: Optional[int] = None
    channel: str
    is_duplicate: bool = False
    delivery_status: str
    message: str
