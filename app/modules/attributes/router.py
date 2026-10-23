from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.catalog import ProductAttribute, Product, Category
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError
from app.modules.attributes.schemas import AttributeCreate, AttributeOut

router = APIRouter(prefix="/attributes", tags=["Module 11: Product Attributes"])

@router.post("", response_model=ResponseSchema[AttributeOut])
def create_attribute(
    data: AttributeCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")

    attr = ProductAttribute(**data.model_dump())
    db.add(attr)
    db.commit()
    db.refresh(attr)
    return ResponseSchema(message="Attribute added successfully", data=AttributeOut.model_validate(attr))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[AttributeOut]])
def get_attributes_for_product(product_id: int, db: Session = Depends(get_db)):
    attrs = db.query(ProductAttribute).filter(ProductAttribute.product_id == product_id).all()
    return ResponseSchema(data=[AttributeOut.model_validate(a) for a in attrs])

@router.get("/filter", response_model=ResponseSchema[List[AttributeOut]])
def filter_attributes_by_name_and_value(
    name: Optional[str] = Query(None),
    value: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ProductAttribute)
    if name:
        query = query.filter(ProductAttribute.name.ilike(f"%{name}%"))
    if value:
        query = query.filter(ProductAttribute.value.ilike(f"%{value}%"))
    return ResponseSchema(data=[AttributeOut.model_validate(a) for a in query.limit(100).all()])

@router.delete("/{attribute_id}", response_model=ResponseSchema[MessageResponse])
def delete_attribute(
    attribute_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    attr = db.query(ProductAttribute).filter(ProductAttribute.id == attribute_id).first()
    if not attr:
        raise NotFoundError("Attribute not found")
    db.delete(attr)
    db.commit()
    return ResponseSchema(message="Attribute removed successfully", data=MessageResponse(message="Attribute deleted"))
