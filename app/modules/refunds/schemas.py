from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import PaymentStatus

class RefundRequest(BaseModel):
    order_id: int
    amount: float = Field(gt=0)
    reason: str
    idempotency_key: Optional[str] = None

class RefundOut(BaseModel):
    id: int
    payment_id: int
    order_id: int
    amount: float
    reason: str
    status: PaymentStatus
    gateway_refund_id: Optional[str] = None
    processed_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
