import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.engagement import SupportTicket, TicketMessage
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, TicketStatus, AuditAction
from app.core.exceptions import NotFoundError, ForbiddenError
from app.core.audit import log_audit
from app.modules.support_tickets.schemas import (
    TicketCreate, TicketMessageCreate, TicketStatusUpdate, TicketOut, TicketMessageOut
)

router = APIRouter(prefix="/support-tickets", tags=["Module 40: Customer Support Tickets"])

@router.post("", response_model=ResponseSchema[TicketOut])
def create_ticket(
    data: TicketCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    ticket_num = f"TCK-{uuid.uuid4().hex[:8].upper()}"
    ticket = SupportTicket(
        ticket_number=ticket_num,
        user_id=current_user.id,
        subject=data.subject,
        description=data.description,
        order_id=data.order_id,
        product_id=data.product_id,
        priority=data.priority,
        status=TicketStatus.OPEN
    )
    db.add(ticket)
    db.flush()

    # Initial message
    first_msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        message=data.description
    )
    db.add(first_msg)
    db.commit()
    db.refresh(ticket)
    log_audit(db, AuditAction.CREATE, "SupportTicket", str(ticket.id), current_user.id)
    return ResponseSchema(message="Support ticket created", data=TicketOut.model_validate(ticket))

@router.get("", response_model=ResponseSchema[List[TicketOut]])
def list_tickets(
    status: Optional[TicketStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(SupportTicket)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(SupportTicket.user_id == current_user.id)
    if status:
        query = query.filter(SupportTicket.status == status)
    tickets = query.order_by(SupportTicket.created_at.desc()).all()
    return ResponseSchema(data=[TicketOut.model_validate(t) for t in tickets])

@router.get("/{ticket_id}", response_model=ResponseSchema[TicketOut])
def get_ticket(
    ticket_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundError("Ticket not found")

    if current_user.role == UserRole.CUSTOMER and ticket.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    return ResponseSchema(data=TicketOut.model_validate(ticket))

@router.post("/{ticket_id}/messages", response_model=ResponseSchema[TicketMessageOut])
def reply_to_ticket(
    ticket_id: int,
    data: TicketMessageCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundError("Ticket not found")

    if current_user.role == UserRole.CUSTOMER and ticket.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    msg = TicketMessage(
        ticket_id=ticket.id,
        sender_id=current_user.id,
        message=data.message,
        attachment_url=data.attachment_url
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return ResponseSchema(message="Message sent", data=TicketMessageOut.model_validate(msg))

@router.put("/{ticket_id}/status", response_model=ResponseSchema[TicketOut])
def update_ticket_status(
    ticket_id: int,
    data: TicketStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()
    if not ticket:
        raise NotFoundError("Ticket not found")

    ticket.status = data.status
    if data.assigned_to_id is not None:
        ticket.assigned_to_id = data.assigned_to_id

    db.commit()
    db.refresh(ticket)
    log_audit(db, AuditAction.STATUS_CHANGE, "SupportTicket", str(ticket.id), current_user.id, new_values={"status": data.status.value})
    return ResponseSchema(message="Ticket status updated", data=TicketOut.model_validate(ticket))
