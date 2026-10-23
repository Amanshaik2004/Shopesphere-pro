from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import ExchangeStatus

class ExchangeCreate(BaseModel):
    order_id: int
    original_item_id: int
    replacement_variant_id: Optional[int] = None
    notes: Optional[str] = None

class ExchangeReviewRequest(BaseModel):
    is_approved: bool
    notes: Optional[str] = None

class ExchangeOut(BaseModel):
    id: int
    order_id: int
    user_id: int
    original_item_id: int
    replacement_variant_id: Optional[int] = None
    status: ExchangeStatus
    approved_by_id: Optional[int] = None
    notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
