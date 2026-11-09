from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.segmentation import CustomerSegment, CustomerSegmentMember, CustomerTag, CustomerNote
from app.models.users import User
from app.models.orders import Order
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, UserStatus, AuditAction, OrderStatus
from app.core.exceptions import NotFoundError, BadRequestError, ConflictError
from app.core.audit import log_audit
from app.modules.customer_segments.schemas import (
    CustomerSegmentCreate, CustomerSegmentUpdate, CustomerSegmentOut,
    SegmentMemberAddRequest, CustomerTagCreate, CustomerTagOut,
    CustomerNoteCreate, CustomerNoteOut, AccountSuspendRequest,
    AccountRestrictionsRequest
)

router = APIRouter(prefix="", tags=["Module 3.5: Customer Segmentation & Account Controls"])

# ----------------- Customer Segments CRUD -----------------

@router.post("/customer-segments", response_model=ResponseSchema[CustomerSegmentOut])
def create_customer_segment(
    data: CustomerSegmentCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    code = data.code.upper().strip()
    if db.query(CustomerSegment).filter(CustomerSegment.code == code).first():
        raise ConflictError(f"Customer segment code '{code}' already exists")

    segment = CustomerSegment(**data.model_dump())
    segment.code = code
    db.add(segment)
    db.commit()
    db.refresh(segment)
    log_audit(db, AuditAction.CREATE, "CustomerSegment", str(segment.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Customer segment created", data=CustomerSegmentOut.model_validate(segment))

@router.get("/customer-segments", response_model=ResponseSchema[List[CustomerSegmentOut]])
def get_customer_segments(db: Session = Depends(get_db)):
    segments = db.query(CustomerSegment).all()
    results = []
    for s in segments:
        m_count = db.query(CustomerSegmentMember).filter(CustomerSegmentMember.segment_id == s.id).count()
        out = CustomerSegmentOut.model_validate(s)
        out.members_count = m_count
        results.append(out)
    return ResponseSchema(data=results)

@router.get("/customer-segments/{segment_id}", response_model=ResponseSchema[CustomerSegmentOut])
def get_customer_segment_by_id(segment_id: int, db: Session = Depends(get_db)):
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise NotFoundError("Segment not found")
    m_count = db.query(CustomerSegmentMember).filter(CustomerSegmentMember.segment_id == segment.id).count()
    out = CustomerSegmentOut.model_validate(segment)
    out.members_count = m_count
    return ResponseSchema(data=out)

@router.put("/customer-segments/{segment_id}", response_model=ResponseSchema[CustomerSegmentOut])
def update_customer_segment(
    segment_id: int,
    data: CustomerSegmentUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise NotFoundError("Segment not found")

    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(segment, k, v)
    db.commit()
    db.refresh(segment)
    log_audit(db, AuditAction.UPDATE, "CustomerSegment", str(segment.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Segment updated", data=CustomerSegmentOut.model_validate(segment))

@router.delete("/customer-segments/{segment_id}", response_model=ResponseSchema[MessageResponse])
def delete_customer_segment(
    segment_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise NotFoundError("Segment not found")
    db.delete(segment)
    db.commit()
    log_audit(db, AuditAction.DELETE, "CustomerSegment", str(segment_id), current_user.id)
    return ResponseSchema(message="Segment deleted", data=MessageResponse(message="Customer segment deleted"))

@router.post("/customer-segments/{segment_id}/members", response_model=ResponseSchema[dict])
def add_segment_members(
    segment_id: int,
    data: SegmentMemberAddRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    segment = db.query(CustomerSegment).filter(CustomerSegment.id == segment_id).first()
    if not segment:
        raise NotFoundError("Segment not found")

    added = 0
    for uid in data.user_ids:
        existing = db.query(CustomerSegmentMember).filter(
            CustomerSegmentMember.segment_id == segment.id,
            CustomerSegmentMember.user_id == uid
        ).first()
        if not existing:
            member = CustomerSegmentMember(segment_id=segment.id, user_id=uid)
            db.add(member)
            added += 1

    db.commit()
    return ResponseSchema(message=f"Added {added} members to segment {segment.name}", data={"added_count": added})

@router.delete("/customer-segments/{segment_id}/members/{user_id}", response_model=ResponseSchema[MessageResponse])
def remove_segment_member(
    segment_id: int,
    user_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    member = db.query(CustomerSegmentMember).filter(
        CustomerSegmentMember.segment_id == segment_id,
        CustomerSegmentMember.user_id == user_id
    ).first()
    if not member:
        raise NotFoundError("Member not found in this segment")
    db.delete(member)
    db.commit()
    return ResponseSchema(message="Removed member from segment", data=MessageResponse(message="Member removed"))

@router.post("/customer-segments/auto-evaluate", response_model=ResponseSchema[dict])
def auto_evaluate_segments(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    customers = db.query(User).filter(User.role == UserRole.CUSTOMER).all()
    segments = db.query(CustomerSegment).filter(CustomerSegment.is_active == True).all()

    assigned_total = 0
    for cust in customers:
        # Calculate order count & total spend
        orders = db.query(Order).filter(Order.user_id == cust.id, Order.status != OrderStatus.CANCELLED).all()
        order_count = len(orders)
        total_spend = sum(float(o.total_amount) for o in orders)

        for seg in segments:
            if order_count >= seg.min_order_count and total_spend >= float(seg.min_total_spend):
                existing = db.query(CustomerSegmentMember).filter(
                    CustomerSegmentMember.segment_id == seg.id,
                    CustomerSegmentMember.user_id == cust.id
                ).first()
                if not existing:
                    db.add(CustomerSegmentMember(segment_id=seg.id, user_id=cust.id))
                    assigned_total += 1

    db.commit()
    return ResponseSchema(message=f"Evaluated segments. {assigned_total} memberships created.", data={"assigned_total": assigned_total})

# ----------------- Customer Tags & Notes -----------------

@router.post("/customers/{customer_id}/tags", response_model=ResponseSchema[CustomerTagOut])
def add_customer_tag(
    customer_id: int,
    data: CustomerTagCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise NotFoundError("Customer not found")

    tag_clean = data.tag.strip()
    tag_record = db.query(CustomerTag).filter(CustomerTag.user_id == user.id, CustomerTag.tag == tag_clean).first()
    if not tag_record:
        tag_record = CustomerTag(user_id=user.id, tag=tag_clean, created_by_id=current_user.id)
        db.add(tag_record)
        db.commit()
        db.refresh(tag_record)

    return ResponseSchema(message="Tag added", data=CustomerTagOut.model_validate(tag_record))

@router.get("/customers/{customer_id}/tags", response_model=ResponseSchema[List[CustomerTagOut]])
def get_customer_tags(
    customer_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    tags = db.query(CustomerTag).filter(CustomerTag.user_id == customer_id).all()
    return ResponseSchema(data=[CustomerTagOut.model_validate(t) for t in tags])

@router.delete("/customers/{customer_id}/tags/{tag_id}", response_model=ResponseSchema[MessageResponse])
def delete_customer_tag(
    customer_id: int,
    tag_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    tag = db.query(CustomerTag).filter(CustomerTag.id == tag_id, CustomerTag.user_id == customer_id).first()
    if not tag:
        raise NotFoundError("Tag not found")
    db.delete(tag)
    db.commit()
    return ResponseSchema(message="Tag removed", data=MessageResponse(message="Tag removed"))

@router.post("/customers/{customer_id}/notes", response_model=ResponseSchema[CustomerNoteOut])
def add_customer_note(
    customer_id: int,
    data: CustomerNoteCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise NotFoundError("Customer not found")

    note = CustomerNote(
        user_id=user.id,
        author_id=current_user.id,
        content=data.content,
        is_private=data.is_private
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    return ResponseSchema(message="Note added", data=CustomerNoteOut.model_validate(note))

@router.get("/customers/{customer_id}/notes", response_model=ResponseSchema[List[CustomerNoteOut]])
def get_customer_notes(
    customer_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    notes = db.query(CustomerNote).filter(CustomerNote.user_id == customer_id).order_by(CustomerNote.created_at.desc()).all()
    return ResponseSchema(data=[CustomerNoteOut.model_validate(n) for n in notes])

# ----------------- Account Controls: Suspend, Reactivate, Restrict -----------------

@router.post("/customers/{customer_id}/suspend", response_model=ResponseSchema[dict])
def suspend_customer(
    customer_id: int,
    data: AccountSuspendRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise NotFoundError("User not found")

    user.status = UserStatus.SUSPENDED
    note = CustomerNote(
        user_id=user.id,
        author_id=current_user.id,
        content=f"ACCOUNT SUSPENDED: {data.reason}",
        is_private=True
    )
    db.add(note)
    db.commit()
    log_audit(db, AuditAction.ACCOUNT_RESTRICTION, "User", str(user.id), current_user.id, new_values={"status": "suspended", "reason": data.reason})
    return ResponseSchema(message="Customer account suspended", data={"user_id": user.id, "status": user.status.value, "reason": data.reason})

@router.post("/customers/{customer_id}/reactivate", response_model=ResponseSchema[dict])
def reactivate_customer(
    customer_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise NotFoundError("User not found")

    user.status = UserStatus.ACTIVE
    db.commit()
    log_audit(db, AuditAction.STATUS_CHANGE, "User", str(user.id), current_user.id, new_values={"status": "active"})
    return ResponseSchema(message="Customer account reactivated", data={"user_id": user.id, "status": user.status.value})

@router.post("/customers/{customer_id}/restrict", response_model=ResponseSchema[dict])
def set_customer_restrictions(
    customer_id: int,
    data: AccountRestrictionsRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == customer_id).first()
    if not user:
        raise NotFoundError("User not found")

    user.account_restrictions = data.restrictions
    db.commit()
    log_audit(db, AuditAction.ACCOUNT_RESTRICTION, "User", str(user.id), current_user.id, new_values=data.restrictions)
    return ResponseSchema(message="Account restrictions updated", data={"user_id": user.id, "restrictions": user.account_restrictions})
