from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.models.payments import Payment, Refund, PaymentTransaction
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles, get_current_active_user
from app.common.enums import UserRole, PaymentStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.integrations.payments.stripe_gateway import stripe_gateway
from app.modules.refunds.schemas import RefundRequest, RefundOut

router = APIRouter(prefix="/refunds", tags=["Module 31: Refund Management"])

@router.post("", response_model=ResponseSchema[RefundOut])
def process_refund(
    data: RefundRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    payment = db.query(Payment).filter(Payment.order_id == data.order_id).first()
    if not payment or payment.status not in [PaymentStatus.SUCCESSFUL, PaymentStatus.PARTIALLY_REFUNDED]:
        raise BadRequestError("Cannot refund an order without a successful or partially refunded payment")

    # Idempotency check
    if data.idempotency_key:
        existing_txn = db.query(PaymentTransaction).filter(
            PaymentTransaction.order_id == data.order_id,
            PaymentTransaction.transaction_type == "REFUND",
            PaymentTransaction.reference_code == data.idempotency_key
        ).first()
        if existing_txn:
            existing_refund = db.query(Refund).filter(
                Refund.payment_id == payment.id,
                Refund.amount == data.amount
            ).first()
            if existing_refund:
                return ResponseSchema(message="Refund already processed (idempotent)", data=RefundOut.model_validate(existing_refund))

    # Calculate already refunded sum
    total_refunded = db.query(func.sum(Refund.amount)).filter(
        Refund.payment_id == payment.id,
        Refund.status == PaymentStatus.SUCCESSFUL
    ).scalar() or 0.0

    refundable_amount = float(payment.amount) - float(total_refunded)
    if data.amount > refundable_amount:
        raise BadRequestError(f"Refund amount {data.amount} exceeds refundable balance of {refundable_amount}")

    # Process through gateway
    gw_res = stripe_gateway.create_refund(
        charge_or_intent_id=payment.transaction_ref or "pi_mock",
        amount=data.amount,
        reason=data.reason
    )

    refund = Refund(
        payment_id=payment.id,
        order_id=data.order_id,
        amount=data.amount,
        reason=data.reason,
        status=PaymentStatus.SUCCESSFUL,
        gateway_refund_id=gw_res.get("id"),
        processed_by_id=current_user.id
    )
    db.add(refund)

    # Log refund transaction
    ref_code = data.idempotency_key or gw_res.get("id", "ref_mock")
    txn = PaymentTransaction(
        payment_id=payment.id,
        order_id=data.order_id,
        transaction_type="REFUND",
        amount=data.amount,
        status=PaymentStatus.SUCCESSFUL,
        reference_code=ref_code,
        raw_response=str(gw_res)
    )
    db.add(txn)

    # Update payment status if full or partial
    new_total_refunded = float(total_refunded) + data.amount
    if new_total_refunded >= float(payment.amount):
        payment.status = PaymentStatus.REFUNDED
    else:
        payment.status = PaymentStatus.PARTIALLY_REFUNDED

    db.commit()
    db.refresh(refund)
    log_audit(db, AuditAction.FINANCIAL_ADJUSTMENT, "Refund", str(refund.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Refund processed successfully", data=RefundOut.model_validate(refund))

@router.get("/order/{order_id}", response_model=ResponseSchema[List[RefundOut]])
def get_order_refunds(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    refunds = db.query(Refund).filter(Refund.order_id == order_id).all()
    return ResponseSchema(data=[RefundOut.model_validate(r) for r in refunds])
