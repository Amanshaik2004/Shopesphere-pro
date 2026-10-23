from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import PurchaseOrderStatus

class POItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    unit_price: float = Field(gt=0)
    quantity: int = Field(gt=0)

class POCreate(BaseModel):
    supplier_id: int
    warehouse_id: int
    notes: Optional[str] = None
    items: List[POItemCreate]

class POItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    unit_price: float
    quantity: int
    received_quantity: int

    class Config:
        from_attributes = True

class POOut(BaseModel):
    id: int
    po_number: str
    supplier_id: int
    warehouse_id: int
    status: PurchaseOrderStatus
    total_amount: float
    notes: Optional[str] = None
    items: List[POItemOut] = []
    created_at: datetime

    class Config:
        from_attributes = True

class ReceivePORequest(BaseModel):
    item_id: int
    received_quantity: int = Field(gt=0)
