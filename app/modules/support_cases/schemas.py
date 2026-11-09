from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel
from app.common.enums import SupportCaseCategory, SupportCaseStatus, TicketPriority

class CaseMessageCreate(BaseModel):
    message: str
    attachment_url: Optional[str] = None

class CaseMessageOut(BaseModel):
    id: int
    case_id: int
    sender_id: int
    message: str
    attachment_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SupportCaseCreate(BaseModel):
    category: SupportCaseCategory = SupportCaseCategory.GENERAL
    priority: TicketPriority = TicketPriority.MEDIUM
    subject: str
    description: str
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    return_id: Optional[int] = None
    is_dispute: bool = False
    chargeback_amount: float = 0.0

class SupportCaseAssignRequest(BaseModel):
    assigned_to_id: int

class SupportCaseEscalateRequest(BaseModel):
    escalated_to_id: Optional[int] = None
    reason: str

class SupportCaseResolveRequest(BaseModel):
    resolution_notes: str
    dispute_status: Optional[str] = None

class SupportCaseOut(BaseModel):
    id: int
    case_number: str
    user_id: int
    order_id: Optional[int] = None
    payment_id: Optional[int] = None
    return_id: Optional[int] = None
    category: SupportCaseCategory
    priority: TicketPriority
    status: SupportCaseStatus
    subject: str
    description: str
    is_dispute: bool
    chargeback_amount: float
    dispute_status: Optional[str] = None
    escalation_level: int
    escalated_to_id: Optional[int] = None
    assigned_to_id: Optional[int] = None
    resolution_notes: Optional[str] = None
    first_response_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    messages: List[CaseMessageOut] = []
    created_at: datetime

    class Config:
        from_attributes = True

class SupportCaseMetricsOut(BaseModel):
    total_cases: int
    open_cases: int
    escalated_cases: int
    resolved_cases: int
    disputes_count: int
    total_chargeback_amount: float
    average_first_response_hours: float
    average_resolution_hours: float
