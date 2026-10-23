from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import ShippingMethod
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError
from app.core.audit import log_audit
from app.modules.shipping_config.schemas import ShippingMethodCreate, ShippingMethodUpdate, ShippingMethodOut

router = APIRouter(prefix="/shipping-config", tags=["Module 23: Shipping Configuration"])

@router.post("", response_model=ResponseSchema[ShippingMethodOut])
def create_shipping_method(
    data: ShippingMethodCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    method = ShippingMethod(**data.model_dump())
    db.add(method)
    db.commit()
    db.refresh(method)
    log_audit(db, AuditAction.CREATE, "ShippingMethod", str(method.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Shipping method created successfully", data=ShippingMethodOut.model_validate(method))

@router.get("", response_model=ResponseSchema[List[ShippingMethodOut]])
def get_shipping_methods(
    is_active: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(ShippingMethod)
    if is_active is not None:
        query = query.filter(ShippingMethod.is_active == is_active)
    return ResponseSchema(data=[ShippingMethodOut.model_validate(m) for m in query.all()])

@router.get("/{method_id}", response_model=ResponseSchema[ShippingMethodOut])
def get_shipping_method_by_id(method_id: int, db: Session = Depends(get_db)):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if not method:
        raise NotFoundError("Shipping method not found")
    return ResponseSchema(data=ShippingMethodOut.model_validate(method))

@router.put("/{method_id}", response_model=ResponseSchema[ShippingMethodOut])
def update_shipping_method(
    method_id: int,
    data: ShippingMethodUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if not method:
        raise NotFoundError("Shipping method not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(method, key, val)

    db.commit()
    db.refresh(method)
    log_audit(db, AuditAction.UPDATE, "ShippingMethod", str(method.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Shipping method updated successfully", data=ShippingMethodOut.model_validate(method))

@router.delete("/{method_id}", response_model=ResponseSchema[MessageResponse])
def delete_shipping_method(
    method_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if not method:
        raise NotFoundError("Shipping method not found")

    db.delete(method)
    db.commit()
    log_audit(db, AuditAction.DELETE, "ShippingMethod", str(method_id), current_user.id)
    return ResponseSchema(message="Shipping method deleted successfully", data=MessageResponse(message="Shipping method removed"))
