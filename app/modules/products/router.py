from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.session import get_db
from app.models.catalog import Product, Category, Brand, PriceHistory
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.pagination import PaginationParams, PaginatedResponse, PaginatedData, paginate_query
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.products.schemas import ProductCreate, ProductUpdate, ProductOut

router = APIRouter(prefix="/products", tags=["Module 08: Product Management"])

@router.post("", response_model=ResponseSchema[ProductOut])
def create_product(
    data: ProductCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if db.query(Product).filter(or_(Product.slug == data.slug, Product.sku == data.sku)).first():
        raise ConflictError("Product with this slug or SKU already exists")

    if not db.query(Category).filter(Category.id == data.category_id).first():
        raise NotFoundError("Category not found")

    if data.brand_id and not db.query(Brand).filter(Brand.id == data.brand_id).first():
        raise NotFoundError("Brand not found")

    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)

    # Initial price history record
    price_rec = PriceHistory(
        product_id=product.id,
        old_base_price=product.base_price,
        new_base_price=product.base_price,
        old_sale_price=product.sale_price,
        new_sale_price=product.sale_price,
        changed_by_user_id=current_user.id,
        reason="Initial product creation"
    )
    db.add(price_rec)
    db.commit()

    log_audit(db, AuditAction.CREATE, "Product", str(product.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Product created successfully", data=ProductOut.model_validate(product))

@router.get("", response_model=PaginatedResponse[ProductOut])
def get_products(
    search: Optional[str] = Query(None, description="Search by name, description, or SKU"),
    category_id: Optional[int] = Query(None),
    brand_id: Optional[int] = Query(None),
    is_active: Optional[bool] = Query(None),
    is_featured: Optional[bool] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    pagination: PaginationParams = Depends(),
    db: Session = Depends(get_db)
):
    query = db.query(Product)
    if search:
        query = query.filter(or_(
            Product.name.ilike(f"%{search}%"),
            Product.description.ilike(f"%{search}%"),
            Product.sku.ilike(f"%{search}%")
        ))
    if category_id:
        query = query.filter(Product.category_id == category_id)
    if brand_id:
        query = query.filter(Product.brand_id == brand_id)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    if is_featured is not None:
        query = query.filter(Product.is_featured == is_featured)
    if min_price is not None:
        query = query.filter(Product.base_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.base_price <= max_price)

    paginated = paginate_query(query, pagination)
    return PaginatedResponse(
        message="Products retrieved successfully",
        data=PaginatedData(
            items=[ProductOut.model_validate(p) for p in paginated.items],
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages
        )
    )

@router.get("/{product_id}", response_model=ResponseSchema[ProductOut])
def get_product_by_id(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")
    
    # Increment view count
    product.views_count += 1
    db.commit()
    return ResponseSchema(data=ProductOut.model_validate(product))

@router.put("/{product_id}", response_model=ResponseSchema[ProductOut])
def update_product(
    product_id: int,
    data: ProductUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")

    old_base_price = product.base_price
    old_sale_price = product.sale_price

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(product, key, val)

    # Track price history if price modified
    if (data.base_price is not None and data.base_price != old_base_price) or (data.sale_price is not None and data.sale_price != old_sale_price):
        price_rec = PriceHistory(
            product_id=product.id,
            old_base_price=old_base_price,
            new_base_price=product.base_price,
            old_sale_price=old_sale_price,
            new_sale_price=product.sale_price,
            changed_by_user_id=current_user.id,
            reason="Product price update"
        )
        db.add(price_rec)

    db.commit()
    db.refresh(product)
    log_audit(db, AuditAction.UPDATE, "Product", str(product.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Product updated successfully", data=ProductOut.model_validate(product))

@router.delete("/{product_id}", response_model=ResponseSchema[MessageResponse])
def deactivate_product(
    product_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise NotFoundError("Product not found")

    product.is_active = False
    db.commit()
    log_audit(db, AuditAction.STATUS_CHANGE, "Product", str(product.id), current_user.id, new_values={"is_active": False})
    return ResponseSchema(message="Product deactivated successfully", data=MessageResponse(message="Product deactivated"))
