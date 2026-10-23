from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import ProductVariant, Product
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.variants.schemas import VariantCreate, VariantUpdate, VariantOut

router = APIRouter(prefix="/variants", tags=["Module 09: Product Variants"])

@router.post("", response_model=ResponseSchema[VariantOut])
def create_variant(
    data: VariantCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")

    if db.query(ProductVariant).filter(ProductVariant.sku == data.sku).first():
        raise ConflictError("Variant with this SKU already exists")

    variant = ProductVariant(**data.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    log_audit(db, AuditAction.CREATE, "ProductVariant", str(variant.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Variant created successfully", data=VariantOut.model_validate(variant))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[VariantOut]])
def get_variants_by_product(product_id: int, db: Session = Depends(get_db)):
    variants = db.query(ProductVariant).filter(ProductVariant.product_id == product_id).all()
    return ResponseSchema(data=[VariantOut.model_validate(v) for v in variants])

@router.get("/{variant_id}", response_model=ResponseSchema[VariantOut])
def get_variant_by_id(variant_id: int, db: Session = Depends(get_db)):
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise NotFoundError("Variant not found")
    return ResponseSchema(data=VariantOut.model_validate(variant))

@router.put("/{variant_id}", response_model=ResponseSchema[VariantOut])
def update_variant(
    variant_id: int,
    data: VariantUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise NotFoundError("Variant not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(variant, key, val)

    db.commit()
    db.refresh(variant)
    log_audit(db, AuditAction.UPDATE, "ProductVariant", str(variant.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Variant updated successfully", data=VariantOut.model_validate(variant))

@router.delete("/{variant_id}", response_model=ResponseSchema[MessageResponse])
def delete_variant(
    variant_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    variant = db.query(ProductVariant).filter(ProductVariant.id == variant_id).first()
    if not variant:
        raise NotFoundError("Variant not found")

    db.delete(variant)
    db.commit()
    log_audit(db, AuditAction.DELETE, "ProductVariant", str(variant_id), current_user.id)
    return ResponseSchema(message="Variant deleted successfully", data=MessageResponse(message="Variant removed"))
