from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import Category, Product
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError, ConflictError
from app.core.audit import log_audit
from app.modules.categories.schemas import CategoryCreate, CategoryUpdate, CategoryOut

router = APIRouter(prefix="/categories", tags=["Module 06: Product Category Management"])

@router.post("", response_model=ResponseSchema[CategoryOut])
def create_category(
    data: CategoryCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if db.query(Category).filter(Category.slug == data.slug).first():
        raise ConflictError("Category with this slug already exists")
    
    if data.parent_id:
        parent = db.query(Category).filter(Category.id == data.parent_id).first()
        if not parent:
            raise NotFoundError("Parent category not found")

    cat = Category(**data.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    log_audit(db, AuditAction.CREATE, "Category", str(cat.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Category created successfully", data=CategoryOut.model_validate(cat))

@router.get("", response_model=ResponseSchema[List[CategoryOut]])
def get_categories(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(Category).filter(Category.parent_id == None)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    categories = query.all()
    return ResponseSchema(data=[CategoryOut.model_validate(c) for c in categories])

@router.get("/{category_id}", response_model=ResponseSchema[CategoryOut])
def get_category_by_id(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise NotFoundError("Category not found")
    return ResponseSchema(data=CategoryOut.model_validate(cat))

@router.put("/{category_id}", response_model=ResponseSchema[CategoryOut])
def update_category(
    category_id: int,
    data: CategoryUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise NotFoundError("Category not found")

    if data.slug and data.slug != cat.slug:
        if db.query(Category).filter(Category.slug == data.slug).first():
            raise ConflictError("Category slug already taken")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)

    db.commit()
    db.refresh(cat)
    log_audit(db, AuditAction.UPDATE, "Category", str(cat.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Category updated successfully", data=CategoryOut.model_validate(cat))

@router.delete("/{category_id}", response_model=ResponseSchema[MessageResponse])
def delete_category(
    category_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise NotFoundError("Category not found")

    # Prevent deletion if products exist
    has_products = db.query(Product).filter(Product.category_id == category_id).first()
    if has_products:
        raise BadRequestError("Cannot delete category with associated products. Deactivate it instead.")

    db.delete(cat)
    db.commit()
    log_audit(db, AuditAction.DELETE, "Category", str(category_id), current_user.id)
    return ResponseSchema(message="Category deleted successfully", data=MessageResponse(message="Category removed"))
