from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Order, OrderCancellation, OrderStatusHistory
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.payments import Payment, Refund
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user
from app.common.enums import UserRole, OrderStatus, PaymentStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError, ForbiddenError
from app.core.audit import log_audit
from app.modules.cancellations.schemas import CancellationRequest, CancellationOut

router = APIRouter(prefix="/cancellations", tags=["Module 28: Order Cancellation"])

@router.post("", response_model=ResponseSchema[CancellationOut])
def request_cancellation(
    req: CancellationRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == req.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise BadRequestError(f"Cannot cancel order in '{order.status.value}' status")

    existing_canc = db.query(OrderCancellation).filter(OrderCancellation.order_id == order.id).first()
    if existing_canc:
        raise BadRequestError("Cancellation already requested for this order")

    # Release reserved inventory
    for item in order.items:
        inv = db.query(InventoryItem).filter(
            InventoryItem.product_id == item.product_id,
            InventoryItem.variant_id == item.variant_id
        ).first()
        if inv and inv.reserved_quantity >= item.quantity:
            inv.reserved_quantity -= item.quantity
            movement = InventoryMovement(
                inventory_item_id=inv.id,
                movement_type="RELEASE",
                quantity=item.quantity,
                reference_type="CANCELLATION",
                note=f"Stock released due to cancellation of order {order.order_number}"
            )
            db.add(movement)

    # Check payment for refund initiation
    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    refund_needed = False
    if payment and payment.status == PaymentStatus.SUCCESSFUL:
        refund_needed = True
        refund = Refund(
            payment_id=payment.id,
            order_id=order.id,
            amount=payment.amount,
            reason=f"Order cancellation: {req.reason}",
            status=PaymentStatus.PENDING
        )
        db.add(refund)

    cancellation = OrderCancellation(
        order_id=order.id,
        requested_by_id=current_user.id,
        reason=req.reason,
        is_approved=True,
        refund_initiated=refund_needed
    )
    db.add(cancellation)

    order.status = OrderStatus.CANCELLED
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status=OrderStatus.CANCELLED,
        changed_by_id=current_user.id,
        comment=f"Order cancelled: {req.reason}"
    )
    db.add(history)
    db.commit()
    db.refresh(cancellation)

    log_audit(db, AuditAction.STATUS_CHANGE, "Order", str(order.id), current_user.id, new_values={"status": "CANCELLED", "reason": req.reason})
    return ResponseSchema(message="Order cancelled and inventory released", data=CancellationOut.model_validate(cancellation))

@router.get("/{order_id}", response_model=ResponseSchema[CancellationOut])
def get_cancellation_details(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    canc = db.query(OrderCancellation).filter(OrderCancellation.order_id == order_id).first()
    if not canc:
        raise NotFoundError("No cancellation record found for this order")
    return ResponseSchema(data=CancellationOut.model_validate(canc))
