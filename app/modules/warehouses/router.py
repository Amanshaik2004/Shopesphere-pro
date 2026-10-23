from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.inventory import Warehouse, InventoryItem
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, ConflictError
from app.core.audit import log_audit
from app.modules.warehouses.schemas import WarehouseCreate, WarehouseUpdate, WarehouseOut
from app.modules.inventory.schemas import InventoryItemOut

router = APIRouter(prefix="/warehouses", tags=["Module 14: Warehouse Management"])

@router.post("", response_model=ResponseSchema[WarehouseOut])
def create_warehouse(
    data: WarehouseCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    if db.query(Warehouse).filter(Warehouse.code == data.code).first():
        raise ConflictError("Warehouse code already exists")

    wh = Warehouse(**data.model_dump())
    db.add(wh)
    db.commit()
    db.refresh(wh)
    log_audit(db, AuditAction.CREATE, "Warehouse", str(wh.id), current_user.id, new_values=data.model_dump())
    return ResponseSchema(message="Warehouse created successfully", data=WarehouseOut.model_validate(wh))

@router.get("", response_model=ResponseSchema[List[WarehouseOut]])
def get_warehouses(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(Warehouse)
    if is_active is not None:
        query = query.filter(Warehouse.is_active == is_active)
    return ResponseSchema(data=[WarehouseOut.model_validate(w) for w in query.all()])

@router.get("/{warehouse_id}", response_model=ResponseSchema[WarehouseOut])
def get_warehouse_by_id(
    warehouse_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")
    return ResponseSchema(data=WarehouseOut.model_validate(wh))

@router.put("/{warehouse_id}", response_model=ResponseSchema[WarehouseOut])
def update_warehouse(
    warehouse_id: int,
    data: WarehouseUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    wh = db.query(Warehouse).filter(Warehouse.id == warehouse_id).first()
    if not wh:
        raise NotFoundError("Warehouse not found")

    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(wh, key, val)

    db.commit()
    db.refresh(wh)
    log_audit(db, AuditAction.UPDATE, "Warehouse", str(wh.id), current_user.id, new_values=data.model_dump(exclude_unset=True))
    return ResponseSchema(message="Warehouse updated successfully", data=WarehouseOut.model_validate(wh))

@router.get("/{warehouse_id}/stock", response_model=ResponseSchema[List[InventoryItemOut]])
def get_warehouse_stock(
    warehouse_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    items = db.query(InventoryItem).filter(InventoryItem.warehouse_id == warehouse_id).all()
    return ResponseSchema(data=[InventoryItemOut.model_validate(i) for i in items])
