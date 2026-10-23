from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import PaymentStatus, PaymentMethod

class PaymentProcessRequest(BaseModel):
    order_id: int
    payment_method: PaymentMethod = PaymentMethod.STRIPE
    idempotency_key: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    order_id: int
    payment_method: PaymentMethod
    amount: float
    currency: str
    status: PaymentStatus
    transaction_ref: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WebhookPayload(BaseModel):
    event_type: str
    payment_intent_id: str
    status: str
    amount: Optional[float] = None
