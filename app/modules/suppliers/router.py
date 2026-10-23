from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.suppliers import Supplier
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.suppliers.schemas import SupplierCreate, SupplierUpdate, SupplierOut

router = APIRouter(prefix="/suppliers", tags=["Module 43: Seller & Supplier Management"])

@router.post("", response_model=ResponseSchema[SupplierOut])
def register_supplier(
    data: SupplierCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    if db.query(Supplier).filter(Supplier.name == data.name).first():
        raise ConflictError("Supplier with this name already exists")

    supplier = Supplier(**data.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    log_audit(db, AuditAction.CREATE, "Supplier", str(supplier.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Supplier registered successfully", data=SupplierOut.model_validate(supplier))

@router.get("", response_model=ResponseSchema[List[SupplierOut]])
def get_suppliers(
    status: Optional[str] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(Supplier)
    if status:
        query = query.filter(Supplier.status == status)
    return ResponseSchema(data=[SupplierOut.model_validate(s) for s in query.all()])

@router.get("/{supplier_id}", response_model=ResponseSchema[SupplierOut])
def get_supplier_by_id(
    supplier_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise NotFoundError("Supplier not found")
    return ResponseSchema(data=SupplierOut.model_validate(supplier))

@router.put("/{supplier_id}", response_model=ResponseSchema[SupplierOut])
def update_supplier(
    supplier_id: int,
    data: SupplierUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.PRODUCT_MANAGER)),
    db: Session = Depends(get_db)
):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise NotFoundError("Supplier not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(supplier, key, val)

    db.commit()
    db.refresh(supplier)
    log_audit(db, AuditAction.UPDATE, "Supplier", str(supplier.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Supplier updated successfully", data=SupplierOut.model_validate(supplier))
