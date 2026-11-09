from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class CustomerSegmentCreate(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    min_order_count: int = 0
    min_total_spend: float = 0.0
    purchase_limit_per_order: Optional[float] = None
    is_active: bool = True

class CustomerSegmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    min_order_count: Optional[int] = None
    min_total_spend: Optional[float] = None
    purchase_limit_per_order: Optional[float] = None
    is_active: Optional[bool] = None

class CustomerSegmentOut(BaseModel):
    id: int
    name: str
    code: str
    description: Optional[str] = None
    min_order_count: int
    min_total_spend: float
    purchase_limit_per_order: Optional[float] = None
    is_active: bool
    members_count: int = 0

    class Config:
        from_attributes = True

class SegmentMemberAddRequest(BaseModel):
    user_ids: List[int]

class CustomerTagCreate(BaseModel):
    tag: str

class CustomerTagOut(BaseModel):
    id: int
    user_id: int
    tag: str
    created_at: datetime

    class Config:
        from_attributes = True

class CustomerNoteCreate(BaseModel):
    content: str
    is_private: bool = True

class CustomerNoteOut(BaseModel):
    id: int
    user_id: int
    author_id: Optional[int] = None
    content: str
    is_private: bool
    created_at: datetime

    class Config:
        from_attributes = True

class AccountSuspendRequest(BaseModel):
    reason: str

class AccountRestrictionsRequest(BaseModel):
    restrictions: Dict[str, Any]
