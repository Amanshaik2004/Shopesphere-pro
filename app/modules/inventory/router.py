from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.inventory import InventoryItem, InventoryMovement, Warehouse
from app.models.catalog import Product, ProductVariant
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction
from app.core.exceptions import NotFoundError, InsufficientStockError
from app.core.audit import log_audit
from app.modules.inventory.schemas import StockAdjustmentRequest, InventoryItemOut

router = APIRouter(prefix="/inventory", tags=["Module 13: Inventory Management"])

@router.post("/adjust", response_model=ResponseSchema[InventoryItemOut])
def adjust_stock(
    data: StockAdjustmentRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    if not db.query(Product).filter(Product.id == data.product_id).first():
        raise NotFoundError("Product not found")

    if not db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first():
        raise NotFoundError("Warehouse not found")

    item = db.query(InventoryItem).filter(
        InventoryItem.product_id == data.product_id,
        InventoryItem.variant_id == data.variant_id,
        InventoryItem.warehouse_id == data.warehouse_id
    ).first()

    if not item:
        if data.adjustment < 0:
            raise InsufficientStockError("Cannot reduce stock for an unrecorded inventory item")
        item = InventoryItem(
            product_id=data.product_id,
            variant_id=data.variant_id,
            warehouse_id=data.warehouse_id,
            quantity=0,
            reserved_quantity=0,
            low_stock_threshold=5
        )
        db.add(item)
        db.flush()

    new_qty = item.quantity + data.adjustment
    if new_qty < item.reserved_quantity:
        raise InsufficientStockError(f"Cannot reduce stock below reserved quantity ({item.reserved_quantity})")

    movement_type = "ADD" if data.adjustment > 0 else "REDUCE"
    movement = InventoryMovement(
        inventory_item_id=item.id,
        movement_type=movement_type,
        quantity=abs(data.adjustment),
        reference_type="MANUAL_ADJUSTMENT",
        note=data.reason,
        performed_by_id=current_user.id
    )
    db.add(movement)

    item.quantity = new_qty
    db.commit()
    db.refresh(item)

    log_audit(db, AuditAction.UPDATE, "Inventory", str(item.id), current_user.id, new_values={"adjustment": data.adjustment, "quantity": item.quantity})
    return ResponseSchema(message="Stock adjusted successfully", data=InventoryItemOut.model_validate(item))

@router.get("/product/{product_id}", response_model=ResponseSchema[List[InventoryItemOut]])
def get_stock_by_product(
    product_id: int,
    variant_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryItem).filter(InventoryItem.product_id == product_id)
    if variant_id is not None:
        query = query.filter(InventoryItem.variant_id == variant_id)
    items = query.all()
    return ResponseSchema(data=[InventoryItemOut.model_validate(i) for i in items])
