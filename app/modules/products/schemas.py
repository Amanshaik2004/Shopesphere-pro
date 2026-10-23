from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class ProductCreate(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    category_id: int
    brand_id: Optional[int] = None
    sku: str
    base_price: float = Field(gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    is_active: bool = True
    is_featured: bool = False

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    brand_id: Optional[int] = None
    sku: Optional[str] = None
    base_price: Optional[float] = Field(None, gt=0)
    sale_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None

class ProductOut(BaseModel):
    id: int
    name: str
    slug: str
    description: Optional[str] = None
    category_id: int
    brand_id: Optional[int] = None
    sku: str
    base_price: float
    sale_price: Optional[float] = None
    is_active: bool
    is_featured: bool
    views_count: int
    created_at: datetime

    class Config:
        from_attributes = True
