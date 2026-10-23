from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class ProductMediaCreate(BaseModel):
    product_id: int
    variant_id: Optional[int] = None
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    is_primary: bool = False

class ProductMediaOut(BaseModel):
    id: int
    product_id: int
    variant_id: Optional[int] = None
    file_name: str
    file_url: str
    file_type: str
    file_size: int
    is_primary: bool
    created_at: datetime

    class Config:
        from_attributes = True
