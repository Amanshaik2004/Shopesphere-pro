from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.common.enums import ReservationStatus

class StockAdjustmentRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    warehouse_id: int
    adjustment: int  # positive to add, negative to reduce
    reason: Optional[str] = "Manual stock adjustment"

class InventoryItemOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    warehouse_id: int
    quantity: int
    reserved_quantity: int
    available_quantity: int
    low_stock_threshold: int

    class Config:
        from_attributes = True

class InventoryReservationRequest(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    warehouse_id: int
    quantity: int = Field(..., gt=0)
    order_id: Optional[int] = None
    duration_minutes: int = Field(default=15, ge=1, le=1440)

class InventoryReservationOut(BaseModel):
    id: int
    order_id: Optional[int] = None
    product_id: int
    variant_id: Optional[int] = None
    warehouse_id: int
    quantity: int
    status: ReservationStatus
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True

class InventoryBatchCreate(BaseModel):
    inventory_item_id: int
    batch_number: str
    expiry_date: Optional[datetime] = None
    quantity: int = Field(..., gt=0)
    cost_per_unit: float = Field(default=0.0, ge=0)

class InventoryBatchOut(BaseModel):
    id: int
    inventory_item_id: int
    batch_number: str
    expiry_date: Optional[datetime] = None
    quantity: int
    cost_per_unit: float
    received_date: datetime

    class Config:
        from_attributes = True

class WarehouseAvailabilityOut(BaseModel):
    warehouse_id: int
    warehouse_name: str
    product_id: int
    variant_id: Optional[int] = None
    total_quantity: int
    reserved_quantity: int
    available_quantity: int
    is_low_stock: bool

class StockDiscrepancyRecordRequest(BaseModel):
    inventory_item_id: int
    physical_quantity: int = Field(..., ge=0)
    reason: str

class StockDiscrepancyOut(BaseModel):
    id: int
    inventory_item_id: int
    system_quantity: int
    physical_quantity: int
    discrepancy: int
    reason: str
    is_reconciled: bool
    reconciled_by_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True

class ReconcileDiscrepancyRequest(BaseModel):
    notes: Optional[str] = "Reconciled against physical audit"
