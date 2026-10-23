from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import PaymentStatus

class TransactionOut(BaseModel):
    id: int
    payment_id: int
    order_id: int
    transaction_type: str
    amount: float
    status: PaymentStatus
    reference_code: str
    created_at: datetime

    class Config:
        from_attributes = True
