from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    title: str
    comment: str

class ReviewOut(BaseModel):
    id: int
    product_id: int
    user_id: int
    rating: int
    title: str
    comment: str
    is_verified_purchase: bool
    is_approved: bool
    created_at: datetime

    class Config:
        from_attributes = True

class ProductRatingSummary(BaseModel):
    product_id: int
    average_rating: float
    total_reviews: int
