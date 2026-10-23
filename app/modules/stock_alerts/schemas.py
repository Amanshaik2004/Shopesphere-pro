from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ThresholdUpdate(BaseModel):
    low_stock_threshold: int = Field(ge=0)

class StockAlertOut(BaseModel):
    id: int
    inventory_item_id: int
    product_id: int
    warehouse_id: int
    threshold: int
    current_stock: int
    is_resolved: bool
    resolved_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True

class RestockAlertReport(BaseModel):
    product_id: int
    product_name: str
    warehouse_name: str
    current_stock: int
    threshold: int
    shortage: int
