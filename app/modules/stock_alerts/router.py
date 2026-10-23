from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.inventory import StockAlert, InventoryItem, Warehouse
from app.models.catalog import Product
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import require_roles
from app.common.enums import UserRole
from app.core.exceptions import NotFoundError
from app.tasks.inventory_tasks import check_low_stock_thresholds
from app.modules.stock_alerts.schemas import ThresholdUpdate, StockAlertOut, RestockAlertReport

router = APIRouter(prefix="/stock-alerts", tags=["Module 16: Low-Stock Management"])

@router.put("/threshold/{inventory_item_id}", response_model=ResponseSchema[MessageResponse])
def update_item_threshold(
    inventory_item_id: int,
    data: ThresholdUpdate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    item = db.query(InventoryItem).filter(InventoryItem.id == inventory_item_id).first()
    if not item:
        raise NotFoundError("Inventory item not found")

    item.low_stock_threshold = data.low_stock_threshold
    db.commit()
    return ResponseSchema(message="Threshold updated successfully", data=MessageResponse(message="Threshold updated"))

@router.post("/scan", response_model=ResponseSchema[dict])
def trigger_low_stock_scan(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    result = check_low_stock_thresholds(db)
    return ResponseSchema(message="Low stock scan completed", data=result)

@router.get("", response_model=ResponseSchema[List[StockAlertOut]])
def get_alerts(
    unresolved_only: bool = True,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    query = db.query(StockAlert)
    if unresolved_only:
        query = query.filter(StockAlert.is_resolved == False)
    alerts = query.order_by(StockAlert.created_at.desc()).all()
    return ResponseSchema(data=[StockAlertOut.model_validate(a) for a in alerts])

@router.post("/{alert_id}/resolve", response_model=ResponseSchema[StockAlertOut])
def resolve_alert(
    alert_id: int,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    alert = db.query(StockAlert).filter(StockAlert.id == alert_id).first()
    if not alert:
        raise NotFoundError("Alert not found")

    alert.is_resolved = True
    alert.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    return ResponseSchema(message="Alert resolved", data=StockAlertOut.model_validate(alert))

@router.get("/report", response_model=ResponseSchema[List[RestockAlertReport]])
def get_low_stock_report(
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.INVENTORY_MANAGER)),
    db: Session = Depends(get_db)
):
    items = db.query(InventoryItem).all()
    reports = []
    for item in items:
        if item.available_quantity <= item.low_stock_threshold:
            prod = db.query(Product).filter(Product.id == item.product_id).first()
            wh = db.query(Warehouse).filter(Warehouse.id == item.warehouse_id).first()
            reports.append(RestockAlertReport(
                product_id=item.product_id,
                product_name=prod.name if prod else "Unknown",
                warehouse_name=wh.name if wh else "Unknown",
                current_stock=item.available_quantity,
                threshold=item.low_stock_threshold,
                shortage=max(0, item.low_stock_threshold - item.available_quantity)
            ))
    return ResponseSchema(data=reports)
