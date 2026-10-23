from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import OrderItem, Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ForbiddenError
from app.core.audit import log_audit
from app.modules.orders.schemas import OrderItemOut
from app.modules.order_items.schemas import OrderItemFulfillmentUpdate

router = APIRouter(prefix="/order-items", tags=["Module 26: Order Item Management"])

@router.get("/order/{order_id}", response_model=ResponseSchema[List[OrderItemOut]])
def get_order_items(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    items = db.query(OrderItem).filter(OrderItem.order_id == order_id).all()
    return ResponseSchema(data=[OrderItemOut.model_validate(i) for i in items])

@router.put("/{order_item_id}/fulfillment", response_model=ResponseSchema[OrderItemOut])
def update_item_fulfillment(
    order_item_id: int,
    data: OrderItemFulfillmentUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    item = db.query(OrderItem).filter(OrderItem.id == order_item_id).first()
    if not item:
        raise NotFoundError("Order item not found")

    item.fulfillment_status = data.fulfillment_status
    db.commit()
    db.refresh(item)
    log_audit(db, AuditAction.UPDATE, "OrderItem", str(item.id), current_user.id, new_values={"fulfillment_status": data.fulfillment_status})
    return ResponseSchema(message="Fulfillment status updated", data=OrderItemOut.model_validate(item))
