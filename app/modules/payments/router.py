import uuid
from fastapi import APIRouter, Depends, Header
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.payments import Payment, PaymentTransaction
from app.models.orders import Order, OrderStatusHistory
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user
from app.common.enums import PaymentStatus, OrderStatus, AuditAction, PaymentMethod
from app.core.exceptions import NotFoundError, BadRequestError, ConflictError, PaymentError
from app.core.audit import log_audit
from app.integrations.payments.stripe_gateway import stripe_gateway
from app.modules.payments.schemas import PaymentProcessRequest, PaymentOut, WebhookPayload

router = APIRouter(prefix="/payments", tags=["Module 29: Payment Management"])

@router.post("/process", response_model=ResponseSchema[PaymentOut])
def process_payment(
    data: PaymentProcessRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    payment = db.query(Payment).filter(Payment.order_id == order.id).first()
    if not payment:
        payment = Payment(
            order_id=order.id,
            payment_method=data.payment_method,
            amount=order.total_amount,
            status=PaymentStatus.PENDING
        )
        db.add(payment)
        db.flush()

    # Prevent duplicate payment
    if payment.status == PaymentStatus.SUCCESSFUL:
        raise ConflictError("Payment has already been successfully completed for this order")

    # Check idempotency
    if data.idempotency_key and payment.idempotency_key == data.idempotency_key and payment.status == PaymentStatus.SUCCESSFUL:
        return ResponseSchema(message="Payment already processed (idempotent)", data=PaymentOut.model_validate(payment))

    if data.idempotency_key:
        payment.idempotency_key = data.idempotency_key

    # Call gateway sandbox
    txn_ref = payment.transaction_ref or f"pi_{uuid.uuid4().hex[:16]}"
    gateway_res = stripe_gateway.confirm_payment(txn_ref)

    if gateway_res.get("status") == "succeeded":
        payment.status = PaymentStatus.SUCCESSFUL
        payment.transaction_ref = txn_ref
        payment.gateway_response = str(gateway_res)

        # Log transaction
        txn = PaymentTransaction(
            payment_id=payment.id,
            order_id=order.id,
            transaction_type="CHARGE",
            amount=payment.amount,
            status=PaymentStatus.SUCCESSFUL,
            reference_code=gateway_res.get("charge_id", txn_ref),
            raw_response=str(gateway_res)
        )
        db.add(txn)

        # Move order to confirmed
        order.status = OrderStatus.CONFIRMED
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=OrderStatus.PENDING,
            to_status=OrderStatus.CONFIRMED,
            changed_by_id=current_user.id,
            comment="Payment received successfully. Order confirmed."
        )
        db.add(history)

        # Permanently deduct reserved stock from inventory
        for item in order.items:
            inv = db.query(InventoryItem).filter(
                InventoryItem.product_id == item.product_id,
                InventoryItem.variant_id == item.variant_id
            ).first()
            if inv:
                inv.quantity = max(0, inv.quantity - item.quantity)
                inv.reserved_quantity = max(0, inv.reserved_quantity - item.quantity)
                movement = InventoryMovement(
                    inventory_item_id=inv.id,
                    movement_type="REDUCE",
                    quantity=item.quantity,
                    reference_type="ORDER_FULFILLMENT",
                    reference_id=order.order_number,
                    note="Stock deducted upon confirmed payment"
                )
                db.add(movement)

        db.commit()
        db.refresh(payment)
        log_audit(db, AuditAction.STATUS_CHANGE, "Payment", str(payment.id), current_user.id, new_values={"status": "SUCCESSFUL"})
        return ResponseSchema(message="Payment succeeded", data=PaymentOut.model_validate(payment))
    else:
        payment.status = PaymentStatus.FAILED
        db.commit()
        raise PaymentError("Payment transaction declined by gateway")

@router.post("/webhook", response_model=ResponseSchema[dict])
def payment_gateway_webhook(
    payload: WebhookPayload,
    stripe_signature: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.transaction_ref == payload.payment_intent_id).first()
    if payment and payload.status == "succeeded" and payment.status != PaymentStatus.SUCCESSFUL:
        payment.status = PaymentStatus.SUCCESSFUL
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CONFIRMED
        db.commit()

    return ResponseSchema(message="Webhook processed", data={"received": True})
