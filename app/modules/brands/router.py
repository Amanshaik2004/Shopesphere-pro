from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import Brand, Product
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.brands.schemas import BrandCreate, BrandUpdate, BrandOut

router = APIRouter(prefix="/brands", tags=["Module 07: Brand Management"])

@router.post("", response_model=ResponseSchema[BrandOut])
def create_brand(
    data: BrandCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if db.query(Brand).filter(Brand.slug == data.slug).first():
        raise ConflictError("Brand with this slug already exists")

    brand = Brand(**data.model_dump())
    db.add(brand)
    db.commit()
    db.refresh(brand)
    log_audit(db, AuditAction.CREATE, "Brand", str(brand.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Brand registered successfully", data=BrandOut.model_validate(brand))

@router.get("", response_model=ResponseSchema[List[BrandOut]])
def get_brands(
    search: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Brand)
    if search:
        query = query.filter(Brand.name.ilike(f"%{search}%"))
    if is_active is not None:
        query = query.filter(Brand.is_active == is_active)
    brands = query.all()
    return ResponseSchema(data=[BrandOut.model_validate(b) for b in brands])

@router.get("/{brand_id}", response_model=ResponseSchema[BrandOut])
def get_brand_by_id(brand_id: int, db: Session = Depends(get_db)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise NotFoundError("Brand not found")
    return ResponseSchema(data=BrandOut.model_validate(brand))

@router.put("/{brand_id}", response_model=ResponseSchema[BrandOut])
def update_brand(
    brand_id: int,
    data: BrandUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if not brand:
        raise NotFoundError("Brand not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(brand, key, val)

    db.commit()
    db.refresh(brand)
    log_audit(db, AuditAction.UPDATE, "Brand", str(brand.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Brand updated successfully", data=BrandOut.model_validate(brand))
