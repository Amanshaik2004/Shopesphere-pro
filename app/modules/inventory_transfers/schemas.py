from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import InventoryTransferStatus

class TransferItemCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    quantity: int = Field(gt=0)

class TransferCreate(BaseModel):
    source_warehouse_id: int
    target_warehouse_id: int
    notes: Optional[str] = None
    items: List[TransferItemCreate]

class TransferItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    quantity: int
    dispatched_quantity: int
    received_quantity: int

    class Config:
        from_attributes = True

class TransferOut(BaseModel):
    id: int
    transfer_number: str
    source_warehouse_id: int
    target_warehouse_id: int
    status: InventoryTransferStatus
    requested_by_id: int
    notes: Optional[str] = None
    items: List[TransferItemOut] = []
    created_at: datetime

    class Config:
        from_attributes = True
