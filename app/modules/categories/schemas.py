from typing import Optional, List
from pydantic import BaseModel

class CategoryBase(BaseModel):
    name: str
    slug: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: bool = True
    image_url: Optional[str] = None

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
    is_active: Optional[bool] = None
    image_url: Optional[str] = None

class SubCategoryOut(BaseModel):
    id: int
    name: str
    slug: str
    is_active: bool

    class Config:
        from_attributes = True

class CategoryOut(CategoryBase):
    id: int
    subcategories: List[SubCategoryOut] = []

    class Config:
        from_attributes = True
