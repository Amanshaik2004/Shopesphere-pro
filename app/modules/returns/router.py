import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import ReturnRequest, ReturnItem
from app.models.orders import Order, OrderItem
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, ReturnStatus, OrderStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError
from app.core.audit import log_audit
from app.modules.returns.schemas import ReturnCreate, ReturnReviewRequest, ReturnOut

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

    return_num = f"RET-{uuid.uuid4().hex[:8].upper()}"
    return_req = ReturnRequest(
        order_id=order.id,
        user_id=current_user.id,
        return_number=return_num,
        reason=data.reason,
        status=ReturnStatus.REQUESTED
    )
    db.add(return_req)
    db.flush()

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

    db.commit()
    db.refresh(return_req)
    log_audit(db, AuditAction.CREATE, "ReturnRequest", str(return_req.id), current_user.id)
    return ResponseSchema(message="Return request submitted successfully", data=ReturnOut.model_validate(return_req))

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
    warehouse_id: int = 1,
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
