from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import TicketStatus, TicketPriority

class TicketCreate(BaseModel):
    subject: str
    description: str
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    priority: TicketPriority = TicketPriority.MEDIUM

class TicketMessageCreate(BaseModel):
    message: str
    attachment_url: Optional[str] = None

class TicketStatusUpdate(BaseModel):
    status: TicketStatus
    assigned_to_id: Optional[int] = None

class TicketMessageOut(BaseModel):
    id: int
    ticket_id: int
    sender_id: int
    message: str
    attachment_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class TicketOut(BaseModel):
    id: int
    ticket_number: str
    user_id: int
    order_id: Optional[int] = None
    product_id: Optional[int] = None
    subject: str
    description: str
    priority: TicketPriority
    status: TicketStatus
    assigned_to_id: Optional[int] = None
    messages: List[TicketMessageOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
