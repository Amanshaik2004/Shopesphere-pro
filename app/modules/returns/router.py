import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import ReturnRequest, ReturnItem
from app.models.orders import Order, OrderItem
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.payments import Payment, Refund
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, ReturnStatus, OrderStatus, AuditAction, PaymentStatus
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError
from app.core.audit import log_audit
from app.modules.returns.schemas import (
    ReturnCreate, ReturnReviewRequest, ReturnOut, ReturnInspectionRequest
)

router = APIRouter(prefix="/returns", tags=["Module 36: Return Management"])

@router.post("", response_model=ResponseSchema[ReturnOut])
def create_return_request(
    data: ReturnCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    if order.status != OrderStatus.DELIVERED:
        raise BadRequestError("Only delivered orders are eligible for return")

    # Enforce configurable return window: 30 days
    now = datetime.now(timezone.utc)
    order_time = order.updated_at.replace(tzinfo=timezone.utc) if order.updated_at.tzinfo is None else order.updated_at
    if (now - order_time).days > 30:
        raise BadRequestError("Return window has expired (30-day limit from delivery)")

    return_num = f"RET-{uuid.uuid4().hex[:8].upper()}"
    return_req = ReturnRequest(
        order_id=order.id,
        user_id=current_user.id,
        return_number=return_num,
        reason=data.reason,
        evidence_url=data.evidence_url,
        status=ReturnStatus.REQUESTED
    )
    db.add(return_req)
    db.flush()

    calculated_refund = 0.0
    for item_in in data.items:
        o_item = db.query(OrderItem).filter(OrderItem.id == item_in.order_item_id, OrderItem.order_id == order.id).first()
        if not o_item:
            raise NotFoundError(f"Order item {item_in.order_item_id} not part of this order")
        if item_in.quantity > o_item.quantity:
            raise BadRequestError(f"Return quantity exceeds purchased quantity ({o_item.quantity})")

        r_item = ReturnItem(
            return_request_id=return_req.id,
            order_item_id=o_item.id,
            quantity=item_in.quantity,
            condition=item_in.condition
        )
        db.add(r_item)
        calculated_refund += float(o_item.unit_price) * item_in.quantity

    return_req.refund_amount = round(calculated_refund, 2)
    db.commit()
    db.refresh(return_req)
    log_audit(db, AuditAction.CREATE, "ReturnRequest", str(return_req.id), current_user.id)
    return ResponseSchema(message="Return request submitted successfully", data=ReturnOut.model_validate(return_req))

@router.get("", response_model=ResponseSchema[List[ReturnOut]])
def get_returns(
    status: Optional[ReturnStatus] = Query(None),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(ReturnRequest)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(ReturnRequest.user_id == current_user.id)
    if status:
        query = query.filter(ReturnRequest.status == status)
    returns = query.order_by(ReturnRequest.created_at.desc()).all()
    return ResponseSchema(data=[ReturnOut.model_validate(r) for r in returns])

@router.get("/{return_id}", response_model=ResponseSchema[ReturnOut])
def get_return_by_id(
    return_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    return_req = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_req:
        raise NotFoundError("Return request not found")

    if current_user.role == UserRole.CUSTOMER and return_req.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    return ResponseSchema(data=ReturnOut.model_validate(return_req))

@router.put("/{return_id}/review", response_model=ResponseSchema[ReturnOut])
def review_return_request(
    return_id: int,
    data: ReturnReviewRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    return_req = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_req:
        raise NotFoundError("Return request not found")

    if data.is_approved:
        return_req.status = ReturnStatus.APPROVED
        return_req.approved_by_id = current_user.id
        if data.refund_amount is not None:
            return_req.refund_amount = data.refund_amount
    else:
        return_req.status = ReturnStatus.REJECTED
        return_req.rejection_reason = data.rejection_reason or "Return policy requirements not met"

    db.commit()
    db.refresh(return_req)
    log_audit(db, AuditAction.STATUS_CHANGE, "ReturnRequest", str(return_req.id), current_user.id, new_values={"status": return_req.status.value})
    return ResponseSchema(message=f"Return request status: {return_req.status.value}", data=ReturnOut.model_validate(return_req))

@router.post("/{return_id}/receive", response_model=ResponseSchema[ReturnOut])
def receive_returned_items(
    return_id: int,
    warehouse_id: int = Query(1),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    return_req = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_req or return_req.status != ReturnStatus.APPROVED:
        raise BadRequestError("Only approved returns can be received")

    for r_item in return_req.items:
        o_item = db.query(OrderItem).filter(OrderItem.id == r_item.order_item_id).first()
        if o_item:
            inv = db.query(InventoryItem).filter(
                InventoryItem.product_id == o_item.product_id,
                InventoryItem.variant_id == o_item.variant_id
            ).first()
            if inv:
                inv.quantity += r_item.quantity
                movement = InventoryMovement(
                    inventory_item_id=inv.id,
                    movement_type="ADD",
                    quantity=r_item.quantity,
                    reference_type="RETURN",
                    reference_id=return_req.return_number,
                    note="Restocked from customer return"
                )
                db.add(movement)

    return_req.status = ReturnStatus.COMPLETED
    db.commit()
    db.refresh(return_req)
    return ResponseSchema(message="Returned items received and restocked", data=ReturnOut.model_validate(return_req))

@router.post("/{return_id}/inspect", response_model=ResponseSchema[ReturnOut])
def inspect_returned_items(
    return_id: int,
    data: ReturnInspectionRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    return_req = db.query(ReturnRequest).filter(ReturnRequest.id == return_id).first()
    if not return_req:
        raise NotFoundError("Return request not found")

    return_req.inspection_outcome = data.outcome
    return_req.inspection_notes = data.notes

    # If restockable, add back to inventory
    if data.outcome == "RESTOCKABLE":
        for r_item in return_req.items:
            o_item = db.query(OrderItem).filter(OrderItem.id == r_item.order_item_id).first()
            if o_item:
                inv = db.query(InventoryItem).filter(
                    InventoryItem.product_id == o_item.product_id,
                    InventoryItem.variant_id == o_item.variant_id
                ).first()
                if inv:
                    inv.quantity += r_item.quantity
                    movement = InventoryMovement(
                        inventory_item_id=inv.id,
                        movement_type="ADD",
                        quantity=r_item.quantity,
                        reference_type="INSPECTION_RESTOCK",
                        note=f"Restocked after inspection outcome: {data.outcome}"
                    )
                    db.add(movement)

    # If auto issue refund is requested
    if data.auto_issue_refund and return_req.refund_amount and return_req.refund_amount > 0:
        payment = db.query(Payment).filter(Payment.order_id == return_req.order_id, Payment.status == PaymentStatus.SUCCESSFUL).first()
        if payment:
            refund = Refund(
                payment_id=payment.id,
                order_id=return_req.order_id,
                amount=return_req.refund_amount,
                reason=f"Return {return_req.return_number} inspection outcome: {data.outcome}",
                status=PaymentStatus.SUCCESSFUL,
                processed_by_id=current_user.id
            )
            db.add(refund)

    return_req.status = ReturnStatus.COMPLETED
    db.commit()
    db.refresh(return_req)
    log_audit(db, AuditAction.UPDATE, "ReturnRequest", str(return_req.id), current_user.id, new_values={"inspection_outcome": data.outcome, "status": "COMPLETED"})
    return ResponseSchema(message=f"Return inspected with outcome {data.outcome}", data=ReturnOut.model_validate(return_req))
