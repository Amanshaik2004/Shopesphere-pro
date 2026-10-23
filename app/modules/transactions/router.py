from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.payments import PaymentTransaction, Payment
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError, ForbiddenError
from app.modules.transactions.schemas import TransactionOut

router = APIRouter(prefix="/transactions", tags=["Module 30: Payment Transaction History"])

@router.get("/order/{order_id}", response_model=ResponseSchema[List[TransactionOut]])
def get_transactions_by_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    txns = db.query(PaymentTransaction).filter(PaymentTransaction.order_id == order_id).order_by(PaymentTransaction.created_at.desc()).all()
    return ResponseSchema(data=[TransactionOut.model_validate(t) for t in txns])

@router.get("/my-history", response_model=ResponseSchema[List[TransactionOut]])
def get_my_payment_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    user_order_ids = [o.id for o in db.query(Order.id).filter(Order.user_id == current_user.id).all()]
    txns = db.query(PaymentTransaction).filter(PaymentTransaction.order_id.in_(user_order_ids)).order_by(PaymentTransaction.created_at.desc()).all()
    return ResponseSchema(data=[TransactionOut.model_validate(t) for t in txns])
