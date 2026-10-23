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
from app.modules.coupons.schemas import CouponCreate, CouponUpdate, CouponOut

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
