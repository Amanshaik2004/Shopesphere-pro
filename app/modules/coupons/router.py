from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Coupon
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.coupons.schemas import CouponCreate, CouponUpdate, CouponOut, CouponValidateRequest, CouponValidateResponse

router = APIRouter(prefix="/coupons", tags=["Module 20: Coupon Management"])

@router.post("", response_model=ResponseSchema[CouponOut])
def create_coupon(
    data: CouponCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    code = data.code.upper().strip()
    if db.query(Coupon).filter(Coupon.code == code).first():
        raise ConflictError("Coupon code already exists")

    coupon_dict = data.model_dump()
    coupon_dict["code"] = code
    coupon = Coupon(**coupon_dict)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    log_audit(db, AuditAction.CREATE, "Coupon", str(coupon.id), current_user.id, new_values=coupon_dict)
    return ResponseSchema(message="Coupon created successfully", data=CouponOut.model_validate(coupon))

@router.get("", response_model=ResponseSchema[List[CouponOut]])
def get_coupons(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(Coupon)
    if is_active is not None:
        query = query.filter(Coupon.is_active == is_active)
    coupons = query.all()
    return ResponseSchema(data=[CouponOut.model_validate(c) for c in coupons])

@router.get("/{coupon_id}", response_model=ResponseSchema[CouponOut])
def get_coupon_by_id(
    coupon_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise NotFoundError("Coupon not found")
    return ResponseSchema(data=CouponOut.model_validate(coupon))

@router.put("/{coupon_id}", response_model=ResponseSchema[CouponOut])
def update_coupon(
    coupon_id: int,
    data: CouponUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise NotFoundError("Coupon not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(coupon, key, val)

    db.commit()
    db.refresh(coupon)
    log_audit(db, AuditAction.UPDATE, "Coupon", str(coupon.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Coupon updated successfully", data=CouponOut.model_validate(coupon))

@router.delete("/{coupon_id}", response_model=ResponseSchema[MessageResponse])
def delete_coupon(
    coupon_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise NotFoundError("Coupon not found")

    db.delete(coupon)
    db.commit()
    log_audit(db, AuditAction.DELETE, "Coupon", str(coupon_id), current_user.id)
    return ResponseSchema(message="Coupon deleted successfully", data=MessageResponse(message="Coupon removed"))

@router.post("/validate", response_model=ResponseSchema[CouponValidateResponse])
def validate_coupon(
    data: CouponValidateRequest,
    db: Session = Depends(get_db)
):
    from datetime import datetime, timezone
    from app.common.enums import DiscountType
    code = data.code.upper().strip()
    coupon = db.query(Coupon).filter(Coupon.code == code).first()
    if not coupon:
        return ResponseSchema(
            message="Invalid coupon code",
            data=CouponValidateResponse(is_valid=False, discount_amount=0.0, message="Coupon not found")
        )

    now = datetime.now(timezone.utc)
    # Handle timezone naive vs aware
    valid_from = coupon.valid_from.replace(tzinfo=timezone.utc) if coupon.valid_from.tzinfo is None else coupon.valid_from
    valid_to = coupon.valid_to.replace(tzinfo=timezone.utc) if coupon.valid_to.tzinfo is None else coupon.valid_to

    if not coupon.is_active or now < valid_from or now > valid_to:
        return ResponseSchema(
            message="Coupon is expired or inactive",
            data=CouponValidateResponse(is_valid=False, discount_amount=0.0, message="Coupon is expired or inactive")
        )

    if coupon.usage_limit and coupon.usage_count >= coupon.usage_limit:
        return ResponseSchema(
            message="Coupon usage limit reached",
            data=CouponValidateResponse(is_valid=False, discount_amount=0.0, message="Coupon usage limit reached")
        )

    if data.cart_amount < float(coupon.min_purchase_amount):
        return ResponseSchema(
            message=f"Cart total ${data.cart_amount} does not meet minimum purchase of ${coupon.min_purchase_amount}",
            data=CouponValidateResponse(
                is_valid=False,
                discount_amount=0.0,
                message=f"Minimum purchase amount of ${coupon.min_purchase_amount} required"
            )
        )

    if coupon.discount_type == DiscountType.PERCENTAGE:
        discount = round((data.cart_amount * float(coupon.discount_value)) / 100.0, 2)
    else:
        discount = float(coupon.discount_value)

    if coupon.max_discount_amount and discount > float(coupon.max_discount_amount):
        discount = float(coupon.max_discount_amount)

    discount = min(discount, data.cart_amount)

    return ResponseSchema(
        message="Coupon is valid and eligible",
        data=CouponValidateResponse(
            is_valid=True,
            discount_amount=round(discount, 2),
            message="Coupon applied successfully",
            coupon=CouponOut.model_validate(coupon)
        )
    )

