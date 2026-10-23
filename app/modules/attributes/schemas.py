from typing import Optional
from pydantic import BaseModel

class AttributeCreate(BaseModel):
    product_id: int
    category_id: Optional[int] = None
    name: str
    value: str

class AttributeOut(BaseModel):
    id: int
    product_id: int
    category_id: Optional[int] = None
    name: str
    value: str

    class Config:
        from_attributes = True
