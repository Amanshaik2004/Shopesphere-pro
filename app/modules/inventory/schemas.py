from typing import Optional
from pydantic import BaseModel, Field

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
