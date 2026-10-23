from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class DeliveryAssignmentCreate(BaseModel):
    shipment_id: int
    delivery_person_id: int

class DeliveryAttemptRecord(BaseModel):
    is_successful: bool
    confirmation_signature: Optional[str] = None
    proof_of_delivery_url: Optional[str] = None
    failure_reason: Optional[str] = None

class DeliveryAssignmentOut(BaseModel):
    id: int
    shipment_id: int
    delivery_person_id: Optional[int] = None
    attempts_count: int
    max_attempts: int
    confirmation_signature: Optional[str] = None
    proof_of_delivery_url: Optional[str] = None
    failure_reason: Optional[str] = None

    class Config:
        from_attributes = True
