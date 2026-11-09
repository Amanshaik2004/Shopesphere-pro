from typing import List, Optional
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.inventory import (
    InventoryItem, InventoryMovement, Warehouse,
    InventoryReservation, InventoryBatch, StockDiscrepancy
)
from app.models.catalog import Product, ProductVariant
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, AuditAction, ReservationStatus
from app.core.exceptions import NotFoundError, InsufficientStockError, BadRequestError
from app.core.audit import log_audit
from app.modules.inventory.schemas import (
    StockAdjustmentRequest, InventoryItemOut, InventoryReservationRequest,
    InventoryReservationOut, InventoryBatchCreate, InventoryBatchOut,
    WarehouseAvailabilityOut, StockDiscrepancyRecordRequest, StockDiscrepancyOut,
    ReconcileDiscrepancyRequest
)

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


# =========================================================================
# Phase 2: Reservations, Batches, Availability, Discrepancies
# =========================================================================

@router.post("/reserve", response_model=ResponseSchema[InventoryReservationOut])
def reserve_stock(
    data: InventoryReservationRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(
        InventoryItem.product_id == data.product_id,
        InventoryItem.variant_id == data.variant_id,
        InventoryItem.warehouse_id == data.warehouse_id
    ).first()

    if not item or item.available_quantity < data.quantity:
        avail = item.available_quantity if item else 0
        raise InsufficientStockError(f"Insufficient stock to reserve. Requested {data.quantity}, available {avail}")

    item.reserved_quantity += data.quantity
    expires = datetime.now(timezone.utc) + timedelta(minutes=data.duration_minutes)

    res = InventoryReservation(
        order_id=data.order_id,
        product_id=data.product_id,
        variant_id=data.variant_id,
        warehouse_id=data.warehouse_id,
        quantity=data.quantity,
        status=ReservationStatus.ACTIVE,
        expires_at=expires
    )
    db.add(res)

    movement = InventoryMovement(
        inventory_item_id=item.id,
        movement_type="RESERVE",
        quantity=data.quantity,
        reference_type="RESERVATION",
        note=f"Stock reserved for {data.duration_minutes}m"
    )
    db.add(movement)
    db.commit()
    db.refresh(res)

    return ResponseSchema(message="Stock reserved successfully", data=InventoryReservationOut.model_validate(res))


@router.post("/reservations/release-expired", response_model=ResponseSchema[dict])
def release_expired_reservations(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    expired = db.query(InventoryReservation).filter(
        InventoryReservation.status == ReservationStatus.ACTIVE,
        InventoryReservation.expires_at <= now
    ).all()

    released_units = 0
    for r in expired:
        item = db.query(InventoryItem).filter(
            InventoryItem.product_id == r.product_id,
            InventoryItem.variant_id == r.variant_id,
            InventoryItem.warehouse_id == r.warehouse_id
        ).first()
        if item:
            item.reserved_quantity = max(0, item.reserved_quantity - r.quantity)
            movement = InventoryMovement(
                inventory_item_id=item.id,
                movement_type="RELEASE",
                quantity=r.quantity,
                reference_type="RESERVATION_EXPIRY",
                note=f"Reservation #{r.id} expired"
            )
            db.add(movement)
        r.status = ReservationStatus.EXPIRED
        released_units += r.quantity

    db.commit()
    return ResponseSchema(message=f"Released {len(expired)} expired reservations ({released_units} units)", data={"expired_count": len(expired), "released_units": released_units})


@router.post("/batches", response_model=ResponseSchema[InventoryBatchOut])
def create_inventory_batch(
    data: InventoryBatchCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == data.inventory_item_id).first()
    if not item:
        raise NotFoundError("Inventory item not found")

    batch = InventoryBatch(**data.model_dump())
    db.add(batch)

    # Increase item quantity
    item.quantity += data.quantity
    movement = InventoryMovement(
        inventory_item_id=item.id,
        movement_type="ADD",
        quantity=data.quantity,
        reference_type="BATCH_RECEIPT",
        note=f"Batch {data.batch_number} received"
    )
    db.add(movement)
    db.commit()
    db.refresh(batch)

    return ResponseSchema(message="Inventory batch recorded", data=InventoryBatchOut.model_validate(batch))


@router.get("/batches", response_model=ResponseSchema[List[InventoryBatchOut]])
def get_inventory_batches(
    inventory_item_id: Optional[int] = Query(None),
    expiring_days: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryBatch)
    if inventory_item_id:
        query = query.filter(InventoryBatch.inventory_item_id == inventory_item_id)
    if expiring_days:
        cutoff = datetime.now(timezone.utc) + timedelta(days=expiring_days)
        query = query.filter(InventoryBatch.expiry_date != None, InventoryBatch.expiry_date <= cutoff)
    batches = query.order_by(InventoryBatch.received_date.desc()).all()
    return ResponseSchema(data=[InventoryBatchOut.model_validate(b) for b in batches])


@router.get("/warehouse-availability", response_model=ResponseSchema[List[WarehouseAvailabilityOut]])
def get_warehouse_availability(
    product_id: Optional[int] = Query(None),
    warehouse_id: Optional[int] = Query(None),
    db: Session = Depends(get_db)
):
    query = db.query(InventoryItem)
    if product_id:
        query = query.filter(InventoryItem.product_id == product_id)
    if warehouse_id:
        query = query.filter(InventoryItem.warehouse_id == warehouse_id)

    items = query.all()
    results = []
    for it in items:
        wh = db.query(Warehouse).filter(Warehouse.id == it.warehouse_id).first()
        results.append(WarehouseAvailabilityOut(
            warehouse_id=it.warehouse_id,
            warehouse_name=wh.name if wh else "Unknown",
            product_id=it.product_id,
            variant_id=it.variant_id,
            total_quantity=it.quantity,
            reserved_quantity=it.reserved_quantity,
            available_quantity=it.available_quantity,
            is_low_stock=(it.available_quantity <= it.low_stock_threshold)
        ))
    return ResponseSchema(data=results)


@router.post("/discrepancies/record", response_model=ResponseSchema[StockDiscrepancyOut])
def record_stock_discrepancy(
    data: StockDiscrepancyRecordRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == data.inventory_item_id).first()
    if not item:
        raise NotFoundError("Inventory item not found")

    disc_val = data.physical_quantity - item.quantity
    disc = StockDiscrepancy(
        inventory_item_id=item.id,
        system_quantity=item.quantity,
        physical_quantity=data.physical_quantity,
        discrepancy=disc_val,
        reason=data.reason,
        is_reconciled=False
    )
    db.add(disc)
    db.commit()
    db.refresh(disc)

    return ResponseSchema(message="Stock discrepancy recorded", data=StockDiscrepancyOut.model_validate(disc))


@router.get("/discrepancies", response_model=ResponseSchema[List[StockDiscrepancyOut]])
def get_stock_discrepancies(
    is_reconciled: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(StockDiscrepancy)
    if is_reconciled is not None:
        query = query.filter(StockDiscrepancy.is_reconciled == is_reconciled)
    discrepancies = query.order_by(StockDiscrepancy.created_at.desc()).all()
    return ResponseSchema(data=[StockDiscrepancyOut.model_validate(d) for d in discrepancies])


@router.post("/discrepancies/{discrepancy_id}/reconcile", response_model=ResponseSchema[StockDiscrepancyOut])
def reconcile_stock_discrepancy(
    discrepancy_id: int,
    data: ReconcileDiscrepancyRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    disc = db.query(StockDiscrepancy).filter(StockDiscrepancy.id == discrepancy_id).first()
    if not disc:
        raise NotFoundError("Discrepancy record not found")

    item = db.query(InventoryItem).filter(InventoryItem.id == disc.inventory_item_id).first()
    if not item:
        raise NotFoundError("Associated inventory item not found")

    old_q = item.quantity
    item.quantity = disc.physical_quantity
    movement = InventoryMovement(
        inventory_item_id=item.id,
        movement_type="ADJUSTMENT",
        quantity=abs(disc.discrepancy),
        reference_type="DISCREPANCY_RECONCILIATION",
        note=f"{data.notes}: adjusted from {old_q} to {disc.physical_quantity}"
    )
    db.add(movement)

    disc.is_reconciled = True
    disc.reconciled_by_id = current_user.id
    db.commit()
    db.refresh(disc)

    log_audit(db, AuditAction.UPDATE, "InventoryDiscrepancy", str(disc.id), current_user.id, new_values={"reconciled_quantity": disc.physical_quantity, "notes": data.notes})
    return ResponseSchema(message="Stock discrepancy reconciled", data=StockDiscrepancyOut.model_validate(disc))
