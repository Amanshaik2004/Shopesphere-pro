from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Promotion
from app.models.catalog import Category, Product
from app.models.segmentation import CustomerSegment
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.promotions.schemas import PromotionCreate, PromotionUpdate, PromotionOut

router = APIRouter(prefix="/promotions", tags=["Module 21: Promotion Management"])

@router.post("", response_model=ResponseSchema[PromotionOut])
def create_promotion(
    data: PromotionCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if data.end_date <= data.start_date:
        raise BadRequestError("End date must be after start date")

    if data.category_id and not db.query(Category).filter(Category.id == data.category_id).first():
        raise NotFoundError("Category not found")
    if data.product_id and not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")
    if data.customer_segment_id and not db.query(CustomerSegment).filter(CustomerSegment.id == data.customer_segment_id).first():
        raise NotFoundError("Customer segment not found")

    promo = Promotion(**data.model_dump())
    db.add(promo)
    db.commit()
    db.refresh(promo)
    log_audit(db, AuditAction.CREATE, "Promotion", str(promo.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Promotion created successfully", data=PromotionOut.model_validate(promo))

@router.get("", response_model=ResponseSchema[List[PromotionOut]])
def get_promotions(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Promotion)
    if is_active is not None:
        query = query.filter(Promotion.is_active == is_active)
    return ResponseSchema(data=[PromotionOut.model_validate(p) for p in query.all()])

@router.get("/{promotion_id}", response_model=ResponseSchema[PromotionOut])
def get_promotion_by_id(promotion_id: int, db: Session = Depends(get_db)):
    promo = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promo:
        raise NotFoundError("Promotion not found")
    return ResponseSchema(data=PromotionOut.model_validate(promo))

@router.put("/{promotion_id}", response_model=ResponseSchema[PromotionOut])
def update_promotion(
    promotion_id: int,
    data: PromotionUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    promo = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promo:
        raise NotFoundError("Promotion not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(promo, key, val)

    db.commit()
    db.refresh(promo)
    log_audit(db, AuditAction.UPDATE, "Promotion", str(promo.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Promotion updated successfully", data=PromotionOut.model_validate(promo))

@router.delete("/{promotion_id}", response_model=ResponseSchema[MessageResponse])
def delete_promotion(
    promotion_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    promo = db.query(Promotion).filter(Promotion.id == promotion_id).first()
    if not promo:
        raise NotFoundError("Promotion not found")

    db.delete(promo)
    db.commit()
    log_audit(db, AuditAction.DELETE, "Promotion", str(promotion_id), current_user.id)
    return ResponseSchema(message="Promotion deleted successfully", data=MessageResponse(message="Promotion removed"))
