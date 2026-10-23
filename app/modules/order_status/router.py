from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Order, OrderStatusHistory
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, OrderStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.orders.schemas import OrderOut, OrderStatusHistoryOut
from app.modules.order_status.schemas import OrderStatusUpdate

router = APIRouter(prefix="/order-status", tags=["Module 27: Order Status Management"])

VALID_TRANSITIONS = {
    OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
    OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
    OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
    OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
    OrderStatus.DELIVERED: [],
    OrderStatus.CANCELLED: []
}

@router.put("/{order_id}", response_model=ResponseSchema[OrderOut])
def update_order_status(
    order_id: int,
    data: OrderStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    allowed = VALID_TRANSITIONS.get(order.status, [])
    if data.status not in allowed:
        raise BadRequestError(f"Invalid status transition from {order.status.value} to {data.status.value}. Allowed: {[s.value for s in allowed]}")

    from_st = order.status
    order.status = data.status

    history = OrderStatusHistory(
        order_id=order.id,
        from_status=from_st,
        to_status=data.status,
        changed_by_id=current_user.id,
        comment=data.comment or f"Status changed to {data.status.value}"
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    log_audit(db, AuditAction.STATUS_CHANGE, "Order", str(order.id), current_user.id, old_values={"status": from_st.value}, new_values={"status": data.status.value})
    return ResponseSchema(message=f"Order status updated to {data.status.value}", data=OrderOut.model_validate(order))

@router.get("/{order_id}/history", response_model=ResponseSchema[List[OrderStatusHistoryOut]])
def get_status_history(order_id: int, db: Session = Depends(get_db)):
    history = db.query(OrderStatusHistory).filter(OrderStatusHistory.order_id == order_id).order_by(OrderStatusHistory.created_at.asc()).all()
    return ResponseSchema(data=[OrderStatusHistoryOut.model_validate(h) for h in history])
