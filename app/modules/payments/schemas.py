from typing import Optional, List
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
    reconciled: bool = False
    reconciliation_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class WebhookPayload(BaseModel):
    event_type: str
    payment_intent_id: str
    status: str
    amount: Optional[float] = None

class PaymentCallbackPayload(BaseModel):
    event_type: str  # payment.success, payment.failed, payment.pending, payment.timeout, payment.duplicate
    transaction_ref: str
    idempotency_key: Optional[str] = None
    amount: Optional[float] = None
    status: str
    reason: Optional[str] = None

class PaymentReconciliationResponse(BaseModel):
    payment_id: int
    transaction_ref: Optional[str]
    recorded_status: str
    gateway_status: str
    is_matched: bool
    reconciled: bool
    notes: str

class PaymentExceptionOut(BaseModel):
    id: int
    payment_id: Optional[int] = None
    order_id: Optional[int] = None
    exception_type: str
    details: str
    status: str
    resolved_by_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ResolveExceptionRequest(BaseModel):
    resolution_notes: str
    status: str = "RESOLVED"
