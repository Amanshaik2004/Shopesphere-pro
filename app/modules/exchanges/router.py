from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import ExchangeRequest
from app.models.orders import Order, OrderItem
from app.models.inventory import InventoryItem
from app.models.catalog import ProductVariant
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, ExchangeStatus, OrderStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError, InsufficientStockError
from app.core.audit import log_audit
from app.modules.exchanges.schemas import ExchangeCreate, ExchangeReviewRequest, ExchangeOut

router = APIRouter(prefix="/exchanges", tags=["Module 37: Exchange Management"])

@router.post("", response_model=ResponseSchema[ExchangeOut])
def create_exchange_request(
    data: ExchangeCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    if order.status != OrderStatus.DELIVERED:
        raise BadRequestError("Exchanges are only allowed for delivered orders")

    item = db.query(OrderItem).filter(OrderItem.id == data.original_item_id, OrderItem.order_id == order.id).first()
    if not item:
        raise NotFoundError("Original order item not found")

    # Validate replacement variant stock
    if data.replacement_variant_id:
        variant = db.query(ProductVariant).filter(ProductVariant.id == data.replacement_variant_id).first()
        if not variant:
            raise NotFoundError("Replacement variant not found")

        inv = db.query(InventoryItem).filter(
            InventoryItem.product_id == item.product_id,
            InventoryItem.variant_id == data.replacement_variant_id
        ).first()
        if not inv or inv.available_quantity < item.quantity:
            raise InsufficientStockError("Insufficient stock for requested replacement variant")

    exchange = ExchangeRequest(
        order_id=order.id,
        user_id=current_user.id,
        original_item_id=item.id,
        replacement_variant_id=data.replacement_variant_id,
        status=ExchangeStatus.REQUESTED,
        notes=data.notes
    )
    db.add(exchange)
    db.commit()
    db.refresh(exchange)
    log_audit(db, AuditAction.CREATE, "ExchangeRequest", str(exchange.id), current_user.id)
    return ResponseSchema(message="Exchange request submitted", data=ExchangeOut.model_validate(exchange))

@router.put("/{exchange_id}/review", response_model=ResponseSchema[ExchangeOut])
def review_exchange(
    exchange_id: int,
    data: ExchangeReviewRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    exchange = db.query(ExchangeRequest).filter(ExchangeRequest.id == exchange_id).first()
    if not exchange:
        raise NotFoundError("Exchange request not found")

    if data.is_approved:
        exchange.status = ExchangeStatus.APPROVED
        exchange.approved_by_id = current_user.id
    else:
        exchange.status = ExchangeStatus.REJECTED

    if data.notes:
        exchange.notes = f"{exchange.notes or ''} | {data.notes}"

    db.commit()
    db.refresh(exchange)
    log_audit(db, AuditAction.STATUS_CHANGE, "ExchangeRequest", str(exchange.id), current_user.id, new_values={"status": exchange.status.value})
    return ResponseSchema(message=f"Exchange status updated to {exchange.status.value}", data=ExchangeOut.model_validate(exchange))
