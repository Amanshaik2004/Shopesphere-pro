from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import ReturnStatus, WarrantyStatus

class ReturnItemCreate(BaseModel):
    order_item_id: int
    quantity: int = Field(..., gt=0)
    condition: Optional[str] = "UNOPENED"

class ReturnCreate(BaseModel):
    order_id: int
    reason: str
    evidence_url: Optional[str] = None
    items: List[ReturnItemCreate]

class ReturnReviewRequest(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None
    refund_amount: Optional[float] = None

class ReturnInspectionRequest(BaseModel):
    outcome: str = "RESTOCKABLE"  # RESTOCKABLE, DAMAGED, DEFECTIVE, WRONG_ITEM
    notes: Optional[str] = None
    restock_warehouse_id: Optional[int] = None
    auto_issue_refund: bool = True

class ReturnItemOut(BaseModel):
    id: int
    order_item_id: int
    quantity: int
    condition: Optional[str] = None

    class Config:
        from_attributes = True

class ReturnOut(BaseModel):
    id: int
    return_number: str
    order_id: int
    user_id: int
    reason: str
    evidence_url: Optional[str] = None
    inspection_outcome: Optional[str] = None
    inspection_notes: Optional[str] = None
    status: ReturnStatus
    approved_by_id: Optional[int] = None
    rejection_reason: Optional[str] = None
    refund_amount: Optional[float] = None
    items: List[ReturnItemOut] = []
    created_at: datetime

    class Config:
        from_attributes = True

class WarrantyClaimCreate(BaseModel):
    order_item_id: int
    product_id: int
    claim_reason: str
    description: str
    evidence_url: Optional[str] = None

class WarrantyClaimReview(BaseModel):
    status: WarrantyStatus
    resolution_notes: str

class WarrantyClaimOut(BaseModel):
    id: int
    claim_number: str
    user_id: int
    order_item_id: int
    product_id: int
    claim_reason: str
    description: str
    evidence_url: Optional[str] = None
    status: WarrantyStatus
    resolution_notes: Optional[str] = None
    approved_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
