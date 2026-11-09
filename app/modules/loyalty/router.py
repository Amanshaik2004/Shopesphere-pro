from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.loyalty import LoyaltyAccount, LoyaltyRule, LoyaltyTransaction
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, LoyaltyTier, LoyaltyTransactionType, AuditAction, OrderStatus
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.loyalty.schemas import (
    LoyaltyAccountOut, LoyaltyTransactionOut, LoyaltyRedeemRequest,
    LoyaltyRedeemResponse, LoyaltyRuleCreate, LoyaltyRuleOut,
    LoyaltyAdjustmentRequest, LoyaltyReverseRequest
)

router = APIRouter(prefix="/loyalty", tags=["Module 3.4: Loyalty & Reward Management"])

def _get_or_create_account(db: Session, user_id: int) -> LoyaltyAccount:
    account = db.query(LoyaltyAccount).filter(LoyaltyAccount.user_id == user_id).first()
    if not account:
        account = LoyaltyAccount(user_id=user_id, points_balance=0, lifetime_earned=0, lifetime_redeemed=0, tier=LoyaltyTier.BRONZE)
        db.add(account)
        db.commit()
        db.refresh(account)
    return account

def _update_tier(account: LoyaltyAccount):
    earned = account.lifetime_earned
    if earned >= 5000:
        account.tier = LoyaltyTier.PLATINUM
    elif earned >= 2000:
        account.tier = LoyaltyTier.GOLD
    elif earned >= 500:
        account.tier = LoyaltyTier.SILVER
    else:
        account.tier = LoyaltyTier.BRONZE

@router.get("/me/balance", response_model=ResponseSchema[LoyaltyAccountOut])
def get_my_loyalty_balance(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = _get_or_create_account(db, current_user.id)
    rule = db.query(LoyaltyRule).filter(LoyaltyRule.is_active == True).first()
    rate = float(rule.redemption_rate) if rule else 100.0
    dollar_val = round(account.points_balance / rate, 2)

    res = LoyaltyAccountOut.model_validate(account)
    res.approximate_dollar_value = dollar_val
    return ResponseSchema(data=res)

@router.get("/me/transactions", response_model=ResponseSchema[List[LoyaltyTransactionOut]])
def get_my_loyalty_transactions(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = _get_or_create_account(db, current_user.id)
    txns = db.query(LoyaltyTransaction).filter(LoyaltyTransaction.account_id == account.id).order_by(LoyaltyTransaction.created_at.desc()).all()
    return ResponseSchema(data=[LoyaltyTransactionOut.model_validate(t) for t in txns])

@router.post("/redeem", response_model=ResponseSchema[LoyaltyRedeemResponse])
def redeem_points(
    data: LoyaltyRedeemRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    account = _get_or_create_account(db, current_user.id)
    rule = db.query(LoyaltyRule).filter(LoyaltyRule.is_active == True).first()
    min_pts = rule.min_points_to_redeem if rule else 50
    rate = float(rule.redemption_rate) if rule else 100.0

    if data.points < min_pts:
        raise BadRequestError(f"Minimum points required to redeem is {min_pts}")

    if account.points_balance < data.points:
        raise BadRequestError(f"Insufficient points. Available: {account.points_balance}")

    discount = round(data.points / rate, 2)
    account.points_balance -= data.points
    account.lifetime_redeemed += data.points

    txn = LoyaltyTransaction(
        account_id=account.id,
        transaction_type=LoyaltyTransactionType.REDEEM,
        points=-data.points,
        dollar_value=discount,
        reason="Points redeemed for order discount"
    )
    db.add(txn)
    db.commit()
    db.refresh(account)

    return ResponseSchema(
        message="Points successfully redeemed",
        data=LoyaltyRedeemResponse(
            points_redeemed=data.points,
            discount_amount=discount,
            remaining_points=account.points_balance
        )
    )

@router.post("/credit-order/{order_id}", response_model=ResponseSchema[dict])
def credit_order_points(
    order_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if order.status not in [OrderStatus.DELIVERED, OrderStatus.CONFIRMED, OrderStatus.PROCESSING, OrderStatus.SHIPPED]:
        raise BadRequestError("Cannot credit points for an unconfirmed or cancelled order")

    # Prevent duplicate points credit for this order
    existing_txn = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.order_id == order.id,
        LoyaltyTransaction.transaction_type == LoyaltyTransactionType.EARN
    ).first()
    if existing_txn:
        return ResponseSchema(message="Points already credited for this order", data={"credited_points": existing_txn.points})

    account = _get_or_create_account(db, order.user_id)
    rule = db.query(LoyaltyRule).filter(LoyaltyRule.is_active == True).first()
    points_per_dollar = float(rule.points_per_dollar) if rule else 1.0

    # Points earned based on order total amount
    points_earned = int(float(order.total_amount) * points_per_dollar)
    if points_earned > 0:
        account.points_balance += points_earned
        account.lifetime_earned += points_earned
        _update_tier(account)

        txn = LoyaltyTransaction(
            account_id=account.id,
            order_id=order.id,
            transaction_type=LoyaltyTransactionType.EARN,
            points=points_earned,
            dollar_value=float(order.total_amount),
            reason=f"Points earned from order {order.order_number}"
        )
        db.add(txn)
        db.commit()

    return ResponseSchema(message=f"Credited {points_earned} points", data={"credited_points": points_earned, "new_balance": account.points_balance})

@router.post("/reverse", response_model=ResponseSchema[dict])
def reverse_order_points(
    data: LoyaltyReverseRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER, UserRole.FINANCE_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    earn_txn = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.order_id == order.id,
        LoyaltyTransaction.transaction_type == LoyaltyTransactionType.EARN
    ).first()

    account = _get_or_create_account(db, order.user_id)
    reversed_points = 0
    if earn_txn:
        reversed_points = earn_txn.points
        account.points_balance = max(0, account.points_balance - reversed_points)
        txn = LoyaltyTransaction(
            account_id=account.id,
            order_id=order.id,
            transaction_type=LoyaltyTransactionType.REVERSAL,
            points=-reversed_points,
            dollar_value=0.0,
            reason=f"Reversal for order {order.order_number}: {data.reason}"
        )
        db.add(txn)
        db.commit()

    return ResponseSchema(message=f"Reversed {reversed_points} points", data={"reversed_points": reversed_points, "balance": account.points_balance})

@router.post("/rules", response_model=ResponseSchema[LoyaltyRuleOut])
def create_or_update_loyalty_rule(
    data: LoyaltyRuleCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    rule = db.query(LoyaltyRule).filter(LoyaltyRule.name == data.name).first()
    if not rule:
        rule = LoyaltyRule(**data.model_dump())
        db.add(rule)
    else:
        for k, v in data.model_dump().items():
            setattr(rule, k, v)
    db.commit()
    db.refresh(rule)
    log_audit(db, AuditAction.CREATE, "LoyaltyRule", str(rule.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Loyalty rule saved", data=LoyaltyRuleOut.model_validate(rule))

@router.get("/rules", response_model=ResponseSchema[List[LoyaltyRuleOut]])
def get_loyalty_rules(db: Session = Depends(get_db)):
    rules = db.query(LoyaltyRule).all()
    return ResponseSchema(data=[LoyaltyRuleOut.model_validate(r) for r in rules])

@router.post("/adjust", response_model=ResponseSchema[LoyaltyAccountOut])
def adjust_loyalty_balance(
    data: LoyaltyAdjustmentRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.SUPPORT_AGENT)),
    db: Session = Depends(get_db)
):
    account = _get_or_create_account(db, data.user_id)
    account.points_balance = max(0, account.points_balance + data.points)
    if data.points > 0:
        account.lifetime_earned += data.points
    _update_tier(account)

    txn = LoyaltyTransaction(
        account_id=account.id,
        transaction_type=LoyaltyTransactionType.ADJUSTMENT,
        points=data.points,
        dollar_value=0.0,
        reason=f"Admin adjustment: {data.reason}"
    )
    db.add(txn)
    db.commit()
    db.refresh(account)
    log_audit(db, AuditAction.FINANCIAL_ADJUSTMENT, "LoyaltyAccount", str(account.id), current_user.id, new_values={"adjustment": data.points, "reason": data.reason})
    return ResponseSchema(message="Loyalty balance adjusted", data=LoyaltyAccountOut.model_validate(account))

@router.post("/expire-points", response_model=ResponseSchema[dict])
def expire_old_points(
    days: int = Query(365, ge=1),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN)),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    old_txns = db.query(LoyaltyTransaction).filter(
        LoyaltyTransaction.transaction_type == LoyaltyTransactionType.EARN,
        LoyaltyTransaction.created_at < cutoff
    ).all()

    expired_count = 0
    for t in old_txns:
        acc = db.query(LoyaltyAccount).filter(LoyaltyAccount.id == t.account_id).first()
        if acc and acc.points_balance > 0:
            deduct = min(acc.points_balance, t.points)
            acc.points_balance -= deduct
            exp_txn = LoyaltyTransaction(
                account_id=acc.id,
                transaction_type=LoyaltyTransactionType.EXPIRE,
                points=-deduct,
                dollar_value=0.0,
                reason=f"Expired {deduct} points from {t.created_at.strftime('%Y-%m-%d')}"
            )
            db.add(exp_txn)
            expired_count += deduct

    db.commit()
    return ResponseSchema(message=f"Expired total of {expired_count} points", data={"expired_points": expired_count})
