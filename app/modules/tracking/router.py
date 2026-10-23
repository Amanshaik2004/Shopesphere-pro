from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import Shipment, ShipmentTrackingEvent
from app.models.orders import Order, OrderStatusHistory
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, ShipmentStatus, OrderStatus
from app.core.exceptions import NotFoundError
from app.modules.tracking.schemas import TrackingEventCreate, TrackingEventOut

router = APIRouter(prefix="/tracking", tags=["Module 34: Shipment Tracking"])

@router.post("/events", response_model=ResponseSchema[TrackingEventOut])
def add_tracking_event(
    data: TrackingEventCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(Shipment.id == data.shipment_id).first()
    if not shipment:
        raise NotFoundError("Shipment not found")

    shipment.status = data.status
    if data.status == ShipmentStatus.DISPATCHED:
        shipment.shipped_at = datetime.now(timezone.utc)
        order = db.query(Order).filter(Order.id == shipment.order_id).first()
        if order and order.status != OrderStatus.SHIPPED:
            order.status = OrderStatus.SHIPPED
    elif data.status == ShipmentStatus.DELIVERED:
        shipment.delivered_at = datetime.now(timezone.utc)
        order = db.query(Order).filter(Order.id == shipment.order_id).first()
        if order and order.status != OrderStatus.DELIVERED:
            order.status = OrderStatus.DELIVERED

    event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status=data.status,
        location=data.location,
        description=data.description
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return ResponseSchema(message="Tracking event recorded", data=TrackingEventOut.model_validate(event))

@router.get("/{tracking_number}", response_model=ResponseSchema[List[TrackingEventOut]])
def get_tracking_timeline(tracking_number: str, db: Session = Depends(get_db)):
    shipment = db.query(Shipment).filter(Shipment.tracking_number == tracking_number).first()
    if not shipment:
        raise NotFoundError("Tracking number not found")

    events = db.query(ShipmentTrackingEvent).filter(ShipmentTrackingEvent.shipment_id == shipment.id).order_by(ShipmentTrackingEvent.event_time.asc()).all()
    return ResponseSchema(data=[TrackingEventOut.model_validate(e) for e in events])
