from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class PriceUpdateRequest(BaseModel):
    base_price: float = Field(gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    reason: Optional[str] = "Price updated by product manager"

class PriceHistoryOut(BaseModel):
    id: int
    product_id: int
    old_base_price: float
    new_base_price: float
    old_sale_price: Optional[float] = None
    new_sale_price: Optional[float] = None
    changed_by_user_id: Optional[int] = None
    reason: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
