from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import Product, PriceHistory
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.pricing.schemas import PriceUpdateRequest, PriceHistoryOut

router = APIRouter(prefix="/pricing", tags=["Module 12: Product Pricing"])

@router.put("/product/{product_id}", response_model=ResponseSchema[PriceHistoryOut])
def update_product_price(
    product_id: int,
    data: PriceUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")

    if data.sale_price is not None and data.sale_price >= data.base_price:
        raise BadRequestError("Sale price must be strictly less than base price")

    old_base_price = product.base_price
    old_sale_price = product.sale_price

    product.base_price = data.base_price
    product.sale_price = data.sale_price

    history = PriceHistory(
        product_id=product.id,
        old_base_price=old_base_price,
        new_base_price=product.base_price,
        old_sale_price=old_sale_price,
        new_sale_price=product.sale_price,
        changed_by_user_id=current_user.id,
        reason=data.reason
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    log_audit(db, AuditAction.UPDATE, "Pricing", str(product.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Pricing updated and history logged", data=PriceHistoryOut.model_validate(history))

@router.get("/product/{product_id}/history", response_model=ResponseSchema[List[PriceHistoryOut]])
def get_price_history(product_id: int, db: Session = Depends(get_db)):
    if not db.query(Product).filter(Product.id == product_id).first():
        raise NotFoundError("Product not found")
    history = db.query(PriceHistory).filter(PriceHistory.product_id == product_id).order_by(PriceHistory.created_at.desc()).all()
    return ResponseSchema(data=[PriceHistoryOut.model_validate(h) for h in history])
