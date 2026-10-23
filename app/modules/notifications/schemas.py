from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import NotificationChannel

class NotificationCreate(BaseModel):
    user_id: int
    title: str
    message: str
    channel: NotificationChannel = NotificationChannel.IN_APP
    notification_type: str = "INFO"
    data: Optional[str] = None

class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    channel: NotificationChannel
    notification_type: str
    is_read: bool
    data: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
