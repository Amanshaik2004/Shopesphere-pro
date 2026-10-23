import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.suppliers import PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.inventory import Warehouse, InventoryItem, InventoryMovement
from app.models.catalog import Product
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, PurchaseOrderStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.modules.purchase_orders.schemas import POCreate, POOut, ReceivePORequest

router = APIRouter(prefix="/purchase-orders", tags=["Module 44: Purchase Order Management"])

@router.post("", response_model=ResponseSchema[POOut])
def create_purchase_order(
    data: POCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    if not db.query(Supplier).filter(Supplier.id == data.supplier_id).first():
        raise NotFoundError("Supplier not found")
    if not db.query(Warehouse).filter(Warehouse.id == data.warehouse_id).first():
        raise NotFoundError("Warehouse not found")

    po_number = f"PO-{uuid.uuid4().hex[:8].upper()}"
    po = PurchaseOrder(
        po_number=po_number,
        supplier_id=data.supplier_id,
        warehouse_id=data.warehouse_id,
        status=PurchaseOrderStatus.SUBMITTED,
        notes=data.notes,
        ordered_by_id=current_user.id,
        total_amount=0.0
    )
    db.add(po)
    db.flush()

    total = 0.0
    for item_data in data.items:
        if not db.query(Product).filter(Product.id == item_data.product_id).first():
            raise NotFoundError(f"Product {item_data.product_id} not found")

        item_total = item_data.unit_price * item_data.quantity
        total += item_total
        po_item = PurchaseOrderItem(
            purchase_order_id=po.id,
            product_id=item_data.product_id,
            variant_id=item_data.variant_id,
            unit_price=item_data.unit_price,
            quantity=item_data.quantity,
            received_quantity=0
        )
        db.add(po_item)

    po.total_amount = round(total, 2)
    db.commit()
    db.refresh(po)
    log_audit(db, AuditAction.CREATE, "PurchaseOrder", str(po.id), current_user.id)
    return ResponseSchema(message="Purchase order created", data=POOut.model_validate(po))

@router.get("", response_model=ResponseSchema[List[POOut]])
def list_purchase_orders(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    pos = db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()
    return ResponseSchema(data=[POOut.model_validate(p) for p in pos])

@router.get("/{po_id}", response_model=ResponseSchema[POOut])
def get_purchase_order(
    po_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise NotFoundError("Purchase order not found")
    return ResponseSchema(data=POOut.model_validate(po))

@router.post("/{po_id}/receive", response_model=ResponseSchema[POOut])
def receive_po_items(
    po_id: int,
    data: ReceivePORequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise NotFoundError("Purchase order not found")

    item = db.query(PurchaseOrderItem).filter(
        PurchaseOrderItem.id == data.item_id,
        PurchaseOrderItem.purchase_order_id == po.id
    ).first()
    if not item:
        raise NotFoundError("Item not part of this purchase order")

    remaining = item.quantity - item.received_quantity
    if data.received_quantity > remaining:
        raise BadRequestError(f"Received quantity exceeds remaining pending quantity ({remaining})")

    item.received_quantity += data.received_quantity

    # Restock into warehouse inventory
    inv = db.query(InventoryItem).filter(
        InventoryItem.warehouse_id == po.warehouse_id,
        InventoryItem.product_id == item.product_id,
        InventoryItem.variant_id == item.variant_id
    ).first()

    if not inv:
        inv = InventoryItem(
            warehouse_id=po.warehouse_id,
            product_id=item.product_id,
            variant_id=item.variant_id,
            quantity=0,
            reserved_quantity=0,
            low_stock_threshold=5
        )
        db.add(inv)
        db.flush()

    inv.quantity += data.received_quantity
    movement = InventoryMovement(
        inventory_item_id=inv.id,
        movement_type="ADD",
        quantity=data.received_quantity,
        reference_type="PURCHASE_ORDER",
        reference_id=po.po_number,
        note=f"Received against PO {po.po_number}",
        performed_by_id=current_user.id
    )
    db.add(movement)

    # Check if all items received
    all_received = all(i.received_quantity >= i.quantity for i in po.items)
    if all_received:
        po.status = PurchaseOrderStatus.RECEIVED

    db.commit()
    db.refresh(po)
    return ResponseSchema(message="Items received and inventory updated", data=POOut.model_validate(po))
