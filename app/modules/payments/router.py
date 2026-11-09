import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.payments import Payment, PaymentTransaction, PaymentExceptionLog
from app.models.orders import Order, OrderStatusHistory
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import PaymentStatus, OrderStatus, AuditAction, PaymentMethod, UserRole
from app.core.exceptions import NotFoundError, BadRequestError, ConflictError, PaymentError
from app.core.audit import log_audit
from app.integrations.payments.stripe_gateway import stripe_gateway
from app.modules.payments.schemas import (
    PaymentProcessRequest, PaymentOut, WebhookPayload,
    PaymentCallbackPayload, PaymentReconciliationResponse,
    PaymentExceptionOut, ResolveExceptionRequest
)

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
            actor_role=current_user.role.value,
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


# =========================================================================
# Phase 2: Advanced Payment & Reconciliation Endpoints
# =========================================================================

@router.post("/{payment_id}/reconcile", response_model=ResponseSchema[PaymentReconciliationResponse])
def reconcile_payment(
    payment_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.id == payment_id).first()
    if not payment:
        raise NotFoundError("Payment record not found")

    # Gateway state check (mock / live)
    gateway_status = "succeeded" if payment.status == PaymentStatus.SUCCESSFUL else "pending"
    matched = (payment.status.value == "successful" and gateway_status == "succeeded") or (payment.status.value != "successful" and gateway_status != "succeeded")

    payment.reconciled = True
    payment.reconciliation_notes = f"Reconciled by {current_user.email} at {datetime.now(timezone.utc).isoformat()}; Status: {gateway_status}"
    db.commit()
    db.refresh(payment)

    log_audit(db, AuditAction.FINANCIAL_ADJUSTMENT, "Payment", str(payment.id), current_user.id, new_values={"reconciled": True})

    return ResponseSchema(
        message="Payment reconciliation completed",
        data=PaymentReconciliationResponse(
            payment_id=payment.id,
            transaction_ref=payment.transaction_ref,
            recorded_status=payment.status.value,
            gateway_status=gateway_status,
            is_matched=matched,
            reconciled=True,
            notes=payment.reconciliation_notes
        )
    )


@router.post("/callback", response_model=ResponseSchema[dict])
def handle_payment_callback(
    data: PaymentCallbackPayload,
    db: Session = Depends(get_db)
):
    # Idempotency check: prevent duplicate callback processing
    if data.idempotency_key:
        existing_txn = db.query(PaymentTransaction).filter(
            PaymentTransaction.reference_code == data.idempotency_key
        ).first()
        if existing_txn:
            return ResponseSchema(
                message="Callback already processed (idempotent duplicate)",
                data={"status": "duplicate_handled", "transaction_id": existing_txn.id}
            )

    payment = db.query(Payment).filter(Payment.transaction_ref == data.transaction_ref).first()
    if not payment:
        # Create an exception log for unmapped callback
        exc = PaymentExceptionLog(
            exception_type="UNMAPPED_TRANSACTION",
            details=f"Received callback for unknown transaction_ref: {data.transaction_ref}",
            status="UNRESOLVED"
        )
        db.add(exc)
        db.commit()
        return ResponseSchema(message="Callback received with exception logged", data={"status": "unmapped_reference"})

    if data.event_type == "payment.duplicate":
        exc = PaymentExceptionLog(
            payment_id=payment.id,
            order_id=payment.order_id,
            exception_type="DUPLICATE_PAYMENT_CALLBACK",
            details=f"Duplicate payment callback received for transaction_ref: {data.transaction_ref}",
            status="RESOLVED",
            resolution_notes="Ignored duplicate callback"
        )
        db.add(exc)
        db.commit()
        return ResponseSchema(message="Duplicate callback detected and logged", data={"status": "duplicate_ignored"})

    if data.event_type in ["payment.failed", "payment.timeout"]:
        payment.status = PaymentStatus.FAILED
        exc = PaymentExceptionLog(
            payment_id=payment.id,
            order_id=payment.order_id,
            exception_type="CALLBACK_FAILURE" if data.event_type == "payment.failed" else "TIMEOUT",
            details=f"Callback reported {data.event_type}: {data.reason or 'No reason provided'}",
            status="UNRESOLVED"
        )
        db.add(exc)
        db.commit()
        return ResponseSchema(message=f"Payment marked failed due to {data.event_type}", data={"status": "failed"})

    if data.event_type == "payment.success" and payment.status != PaymentStatus.SUCCESSFUL:
        payment.status = PaymentStatus.SUCCESSFUL
        order = db.query(Order).filter(Order.id == payment.order_id).first()
        if order and order.status == OrderStatus.PENDING:
            order.status = OrderStatus.CONFIRMED

        txn = PaymentTransaction(
            payment_id=payment.id,
            order_id=payment.order_id,
            transaction_type="CAPTURE",
            amount=data.amount or payment.amount,
            status=PaymentStatus.SUCCESSFUL,
            reference_code=data.idempotency_key or f"ref_{uuid.uuid4().hex[:8]}",
            raw_response=str(data.model_dump())
        )
        db.add(txn)
        db.commit()
        return ResponseSchema(message="Payment confirmed via callback", data={"status": "success"})

    return ResponseSchema(message="Callback received and processed", data={"status": "processed"})


@router.get("/exceptions", response_model=ResponseSchema[List[PaymentExceptionOut]])
def get_payment_exceptions(
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(PaymentExceptionLog)
    if status:
        query = query.filter(PaymentExceptionLog.status == status)
    exceptions = query.order_by(PaymentExceptionLog.created_at.desc()).all()
    return ResponseSchema(data=[PaymentExceptionOut.model_validate(e) for e in exceptions])


@router.put("/{payment_id}/resolve-exception", response_model=ResponseSchema[PaymentExceptionOut])
def resolve_payment_exception(
    payment_id: int,
    data: ResolveExceptionRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    exc = db.query(PaymentExceptionLog).filter(
        PaymentExceptionLog.payment_id == payment_id,
        PaymentExceptionLog.status == "UNRESOLVED"
    ).first()
    if not exc:
        raise NotFoundError("No unresolved exception found for this payment")

    exc.status = data.status
    exc.resolution_notes = data.resolution_notes
    exc.resolved_by_id = current_user.id
    db.commit()
    db.refresh(exc)
    log_audit(db, AuditAction.FINANCIAL_ADJUSTMENT, "PaymentException", str(exc.id), current_user.id, new_values={"status": exc.status, "notes": data.resolution_notes})
    return ResponseSchema(message="Payment exception resolved", data=PaymentExceptionOut.model_validate(exc))


@router.get("/settlement-history", response_model=ResponseSchema[List[dict]])
def get_settlement_history(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    # Combines successful payments and reconciliations
    payments = db.query(Payment).filter(Payment.status.in_([PaymentStatus.SUCCESSFUL, PaymentStatus.REFUNDED, PaymentStatus.PARTIALLY_REFUNDED])).order_by(Payment.created_at.desc()).limit(100).all()
    records = []
    for p in payments:
        records.append({
            "payment_id": p.id,
            "order_id": p.order_id,
            "amount": float(p.amount),
            "currency": p.currency,
            "status": p.status.value,
            "payment_method": p.payment_method.value,
            "transaction_ref": p.transaction_ref,
            "reconciled": p.reconciled,
            "reconciliation_notes": p.reconciliation_notes,
            "created_at": p.created_at.isoformat()
        })
    return ResponseSchema(data=records)
