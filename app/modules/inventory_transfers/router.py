import uuid
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.inventory import InventoryTransfer, InventoryTransferItem, InventoryItem, InventoryMovement, Warehouse
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, InventoryTransferStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError, InsufficientStockError
from app.core.audit import log_audit
from app.modules.inventory_transfers.schemas import TransferCreate, TransferOut

router = APIRouter(prefix="/inventory-transfers", tags=["Module 15: Inventory Transfers"])

@router.post("", response_model=ResponseSchema[TransferOut])
def create_transfer_request(
    data: TransferCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    if data.source_warehouse_id == data.target_warehouse_id:
        raise BadRequestError("Source and target warehouses cannot be the same")

    if not db.query(Warehouse).filter(Warehouse.id == data.source_warehouse_id).first():
        raise NotFoundError("Source warehouse not found")
    if not db.query(Warehouse).filter(Warehouse.id == data.target_warehouse_id).first():
        raise NotFoundError("Target warehouse not found")

    transfer_num = f"TRF-{uuid.uuid4().hex[:8].upper()}"
    transfer = InventoryTransfer(
        transfer_number=transfer_num,
        source_warehouse_id=data.source_warehouse_id,
        target_warehouse_id=data.target_warehouse_id,
        status=InventoryTransferStatus.REQUESTED,
        requested_by_id=current_user.id,
        notes=data.notes
    )
    db.add(transfer)
    db.flush()

    for item_in in data.items:
        # Check source inventory exists and has sufficient quantity
        source_stock = db.query(InventoryItem).filter(
            InventoryItem.warehouse_id == data.source_warehouse_id,
            InventoryItem.product_id == item_in.product_id,
            InventoryItem.variant_id == item_in.variant_id
        ).first()

        if not source_stock or source_stock.available_quantity < item_in.quantity:
            raise InsufficientStockError(f"Insufficient stock in source warehouse for product ID {item_in.product_id}")

        item = InventoryTransferItem(
            transfer_id=transfer.id,
            product_id=item_in.product_id,
            variant_id=item_in.variant_id,
            quantity=item_in.quantity,
            dispatched_quantity=0,
            received_quantity=0
        )
        db.add(item)

    db.commit()
    db.refresh(transfer)
    log_audit(db, AuditAction.CREATE, "InventoryTransfer", str(transfer.id), current_user.id)
    return ResponseSchema(message="Transfer request created successfully", data=TransferOut.model_validate(transfer))

@router.post("/{transfer_id}/dispatch", response_model=ResponseSchema[TransferOut])
def dispatch_transfer(
    transfer_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    if not transfer:
        raise NotFoundError("Transfer not found")
    if transfer.status not in [InventoryTransferStatus.REQUESTED, InventoryTransferStatus.APPROVED]:
        raise BadRequestError(f"Cannot dispatch transfer in status {transfer.status.value}")

    for item in transfer.items:
        source_stock = db.query(InventoryItem).filter(
            InventoryItem.warehouse_id == transfer.source_warehouse_id,
            InventoryItem.product_id == item.product_id,
            InventoryItem.variant_id == item.variant_id
        ).first()
        if not source_stock or source_stock.available_quantity < item.quantity:
            raise InsufficientStockError(f"Insufficient stock to dispatch item {item.product_id}")

        source_stock.quantity -= item.quantity
        item.dispatched_quantity = item.quantity

        movement = InventoryMovement(
            inventory_item_id=source_stock.id,
            movement_type="TRANSFER_OUT",
            quantity=item.quantity,
            reference_type="INVENTORY_TRANSFER",
            reference_id=transfer.transfer_number,
            performed_by_id=current_user.id
        )
        db.add(movement)

    transfer.status = InventoryTransferStatus.DISPATCHED
    db.commit()
    db.refresh(transfer)
    log_audit(db, AuditAction.STATUS_CHANGE, "InventoryTransfer", str(transfer.id), current_user.id, new_values={"status": "DISPATCHED"})
    return ResponseSchema(message="Transfer dispatched successfully", data=TransferOut.model_validate(transfer))

@router.post("/{transfer_id}/receive", response_model=ResponseSchema[TransferOut])
def receive_transfer(
    transfer_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    transfer = db.query(InventoryTransfer).filter(InventoryTransfer.id == transfer_id).first()
    if not transfer:
        raise NotFoundError("Transfer not found")
    if transfer.status != InventoryTransferStatus.DISPATCHED:
        raise BadRequestError("Only dispatched transfers can be received")

    for item in transfer.items:
        target_stock = db.query(InventoryItem).filter(
            InventoryItem.warehouse_id == transfer.target_warehouse_id,
            InventoryItem.product_id == item.product_id,
            InventoryItem.variant_id == item.variant_id
        ).first()

        if not target_stock:
            target_stock = InventoryItem(
                warehouse_id=transfer.target_warehouse_id,
                product_id=item.product_id,
                variant_id=item.variant_id,
                quantity=0,
                reserved_quantity=0,
                low_stock_threshold=5
            )
            db.add(target_stock)
            db.flush()

        target_stock.quantity += item.dispatched_quantity
        item.received_quantity = item.dispatched_quantity

        movement = InventoryMovement(
            inventory_item_id=target_stock.id,
            movement_type="TRANSFER_IN",
            quantity=item.dispatched_quantity,
            reference_type="INVENTORY_TRANSFER",
            reference_id=transfer.transfer_number,
            performed_by_id=current_user.id
        )
        db.add(movement)

    transfer.status = InventoryTransferStatus.RECEIVED
    db.commit()
    db.refresh(transfer)
    log_audit(db, AuditAction.STATUS_CHANGE, "InventoryTransfer", str(transfer.id), current_user.id, new_values={"status": "RECEIVED"})
    return ResponseSchema(message="Transfer received successfully", data=TransferOut.model_validate(transfer))

@router.get("", response_model=ResponseSchema[List[TransferOut]])
def get_transfers(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    transfers = db.query(InventoryTransfer).order_by(InventoryTransfer.created_at.desc()).all()
    return ResponseSchema(data=[TransferOut.model_validate(t) for t in transfers])
