from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import NotificationChannel, NotificationStatus

class SendMessageRequest(BaseModel):
    recipient: str
    channel: NotificationChannel = NotificationChannel.EMAIL
    subject: Optional[str] = "ShopSphere Update"
    content: str

class DeliveryLogOut(BaseModel):
    id: int
    channel: NotificationChannel
    recipient: str
    status: NotificationStatus
    retry_count: int
    error_message: Optional[str] = None
    sent_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True
