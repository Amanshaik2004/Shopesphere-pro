from typing import Optional
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import AuditAction

class AuditLogOut(BaseModel):
    id: int
    user_id: Optional[int] = None
    action: AuditAction
    entity_type: str
    entity_id: Optional[str] = None
    old_values: Optional[str] = None
    new_values: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
