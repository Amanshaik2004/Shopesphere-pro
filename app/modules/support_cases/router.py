import uuid
from typing import List, Optional
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.support import SupportCase, CaseMessage
from app.models.users import User
from app.models.orders import Order
from app.models.payments import Payment
from app.models.logistics import ReturnRequest
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import (
    UserRole, SupportCaseCategory, SupportCaseStatus, TicketPriority, AuditAction
)
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.core.audit import log_audit
from app.modules.support_cases.schemas import (
    SupportCaseCreate, SupportCaseOut, CaseMessageCreate, CaseMessageOut,
    SupportCaseAssignRequest, SupportCaseEscalateRequest, SupportCaseResolveRequest,
    SupportCaseMetricsOut
)

router = APIRouter(prefix="/support-cases", tags=["Module 3.9: Support & Dispute Management"])

@router.post("", response_model=ResponseSchema[SupportCaseOut])
def create_support_case(
    data: SupportCaseCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if data.order_id and not db.query(Order).filter(Order.id == data.order_id).first():
        raise NotFoundError("Referenced order not found")
    if data.payment_id and not db.query(Payment).filter(Payment.id == data.payment_id).first():
        raise NotFoundError("Referenced payment not found")
    if data.return_id and not db.query(ReturnRequest).filter(ReturnRequest.id == data.return_id).first():
        raise NotFoundError("Referenced return request not found")

    case_num = f"CASE-{uuid.uuid4().hex[:8].upper()}"
    case = SupportCase(
        case_number=case_num,
        user_id=current_user.id,
        order_id=data.order_id,
        payment_id=data.payment_id,
        return_id=data.return_id,
        category=data.category,
        priority=data.priority,
        status=SupportCaseStatus.OPEN,
        subject=data.subject,
        description=data.description,
        is_dispute=data.is_dispute,
        chargeback_amount=data.chargeback_amount,
        dispute_status="UNDER_REVIEW" if data.is_dispute else None
    )
    db.add(case)
    db.flush()

    # Initial message
    init_msg = CaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=data.description
    )
    db.add(init_msg)
    db.commit()
    db.refresh(case)

    log_audit(db, AuditAction.CREATE, "SupportCase", str(case.id), current_user.id)
    return ResponseSchema(message="Support case submitted successfully", data=SupportCaseOut.model_validate(case))

@router.get("", response_model=ResponseSchema[List[SupportCaseOut]])
def get_support_cases(
    category: Optional[SupportCaseCategory] = Query(None),
    status: Optional[SupportCaseStatus] = Query(None),
    is_dispute: Optional[bool] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(SupportCase)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(SupportCase.user_id == current_user.id)
    if category:
        query = query.filter(SupportCase.category == category)
    if status:
        query = query.filter(SupportCase.status == status)
    if is_dispute is not None:
        query = query.filter(SupportCase.is_dispute == is_dispute)

    cases = query.order_by(SupportCase.created_at.desc()).all()
    return ResponseSchema(data=[SupportCaseOut.model_validate(c) for c in cases])

@router.get("/metrics", response_model=ResponseSchema[SupportCaseMetricsOut])
def get_support_case_metrics(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    cases = db.query(SupportCase).all()
    total = len(cases)
    open_c = sum(1 for c in cases if c.status in [SupportCaseStatus.OPEN, SupportCaseStatus.IN_PROGRESS])
    esc_c = sum(1 for c in cases if c.status == SupportCaseStatus.ESCALATED)
    res_c = sum(1 for c in cases if c.status in [SupportCaseStatus.RESOLVED, SupportCaseStatus.CLOSED])
    disputes = [c for c in cases if c.is_dispute]
    chargeback_sum = sum(float(c.chargeback_amount) for c in disputes)

    # Calculate average first response and resolution time
    response_times = []
    resolution_times = []
    for c in cases:
        if c.first_response_at:
            created = c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at
            first_resp = c.first_response_at.replace(tzinfo=timezone.utc) if c.first_response_at.tzinfo is None else c.first_response_at
            response_times.append((first_resp - created).total_seconds() / 3600.0)
        if c.resolved_at:
            created = c.created_at.replace(tzinfo=timezone.utc) if c.created_at.tzinfo is None else c.created_at
            res_at = c.resolved_at.replace(tzinfo=timezone.utc) if c.resolved_at.tzinfo is None else c.resolved_at
            resolution_times.append((res_at - created).total_seconds() / 3600.0)

    avg_resp = round(sum(response_times) / len(response_times), 2) if response_times else 0.0
    avg_res = round(sum(resolution_times) / len(resolution_times), 2) if resolution_times else 0.0

    return ResponseSchema(
        data=SupportCaseMetricsOut(
            total_cases=total,
            open_cases=open_c,
            escalated_cases=esc_c,
            resolved_cases=res_c,
            disputes_count=len(disputes),
            total_chargeback_amount=round(chargeback_sum, 2),
            average_first_response_hours=avg_resp,
            average_resolution_hours=avg_res
        )
    )

@router.get("/{case_id}", response_model=ResponseSchema[SupportCaseOut])
def get_support_case_detail(
    case_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise NotFoundError("Support case not found")

    if current_user.role == UserRole.CUSTOMER and case.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    return ResponseSchema(data=SupportCaseOut.model_validate(case))

@router.post("/{case_id}/messages", response_model=ResponseSchema[CaseMessageOut])
def post_case_message(
    case_id: int,
    data: CaseMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise NotFoundError("Support case not found")

    if current_user.role == UserRole.CUSTOMER and case.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    msg = CaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=data.message,
        attachment_url=data.attachment_url
    )
    db.add(msg)

    # If first staff response, track first_response_at
    if current_user.role != UserRole.CUSTOMER and not case.first_response_at:
        case.first_response_at = datetime.now(timezone.utc)
        if case.status == SupportCaseStatus.OPEN:
            case.status = SupportCaseStatus.IN_PROGRESS

    db.commit()
    db.refresh(msg)
    return ResponseSchema(message="Message added to case conversation", data=CaseMessageOut.model_validate(msg))

@router.put("/{case_id}/assign", response_model=ResponseSchema[SupportCaseOut])
def assign_support_case(
    case_id: int,
    data: SupportCaseAssignRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise NotFoundError("Support case not found")

    assignee = db.query(User).filter(User.id == data.assigned_to_id).first()
    if not assignee:
        raise NotFoundError("Assignee user not found")

    case.assigned_to_id = assignee.id
    if case.status == SupportCaseStatus.OPEN:
        case.status = SupportCaseStatus.IN_PROGRESS
    db.commit()
    db.refresh(case)

    log_audit(db, AuditAction.UPDATE, "SupportCase", str(case.id), current_user.id, new_values={"assigned_to_id": assignee.id})
    return ResponseSchema(message=f"Case assigned to {assignee.full_name}", data=SupportCaseOut.model_validate(case))

@router.put("/{case_id}/escalate", response_model=ResponseSchema[SupportCaseOut])
def escalate_support_case(
    case_id: int,
    data: SupportCaseEscalateRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise NotFoundError("Support case not found")

    case.status = SupportCaseStatus.ESCALATED
    case.escalation_level += 1
    if data.escalated_to_id:
        case.escalated_to_id = data.escalated_to_id

    esc_msg = CaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=f"[ESCALATION LEVEL {case.escalation_level}]: {data.reason}"
    )
    db.add(esc_msg)
    db.commit()
    db.refresh(case)

    log_audit(db, AuditAction.UPDATE, "SupportCase", str(case.id), current_user.id, new_values={"status": "ESCALATED", "level": case.escalation_level, "reason": data.reason})
    return ResponseSchema(message=f"Case escalated to Level {case.escalation_level}", data=SupportCaseOut.model_validate(case))

@router.put("/{case_id}/resolve", response_model=ResponseSchema[SupportCaseOut])
def resolve_support_case(
    case_id: int,
    data: SupportCaseResolveRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    case = db.query(SupportCase).filter(SupportCase.id == case_id).first()
    if not case:
        raise NotFoundError("Support case not found")

    case.status = SupportCaseStatus.RESOLVED
    case.resolution_notes = data.resolution_notes
    case.resolved_at = datetime.now(timezone.utc)
    if data.dispute_status:
        case.dispute_status = data.dispute_status

    res_msg = CaseMessage(
        case_id=case.id,
        sender_id=current_user.id,
        message=f"[RESOLVED]: {data.resolution_notes}"
    )
    db.add(res_msg)
    db.commit()
    db.refresh(case)

    log_audit(db, AuditAction.UPDATE, "SupportCase", str(case.id), current_user.id, new_values={"status": "RESOLVED", "resolution": data.resolution_notes})
    return ResponseSchema(message="Support case resolved", data=SupportCaseOut.model_validate(case))
