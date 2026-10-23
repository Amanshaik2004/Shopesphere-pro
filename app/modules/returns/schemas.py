from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import ReturnStatus

class ReturnItemCreate(BaseModel):
    order_item_id: int
    quantity: int = Field(gt=0)
    condition: Optional[str] = "UNOPENED"

class ReturnCreate(BaseModel):
    order_id: int
    reason: str
    items: List[ReturnItemCreate]

class ReturnReviewRequest(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None
    refund_amount: Optional[float] = None

class ReturnItemOut(BaseModel):
    id: int
    order_item_id: int
    quantity: int
    condition: Optional[str]

    class Config:
        from_attributes = True

class ReturnOut(BaseModel):
    id: int
    return_number: str
    order_id: int
    user_id: int
    reason: str
    status: ReturnStatus
    approved_by_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    items: List[ReturnItemOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
