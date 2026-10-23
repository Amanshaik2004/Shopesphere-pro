from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field

class CODCollectionUpdate(BaseModel):
    collection_status: str  # COLLECTED, FAILED
    notes: Optional[str] = None

class CODReconciliationRequest(BaseModel):
    order_id: int
    notes: Optional[str] = "Reconciled by finance manager"

class CODRecordOut(BaseModel):
    id: int
    order_id: int
    amount: float
    collection_status: str
    collected_by_id: Optional[int] = None
    collected_at: Optional[datetime] = None
    reconciled: bool
    reconciliation_date: Optional[datetime] = None
    notes: Optional[str] = None

    class Config:
        from_attributes = True
