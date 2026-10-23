from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class WishlistAddRequest(BaseModel):
    product_id: int

class WishlistItemOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    base_price: float
    sale_price: Optional[float] = None
    is_available: bool
    created_at: datetime
