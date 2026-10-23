from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import Shipment, ShipmentTrackingEvent, DeliveryAssignment
from app.models.orders import Order, OrderStatusHistory
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles, get_current_active_user
from app.common.enums import UserRole, ShipmentStatus, OrderStatus, AuditAction
from app.core.exceptions import NotFoundError, BadRequestError
from app.core.audit import log_audit
from app.integrations.shipping.provider import shipping_provider
from app.modules.shipments.schemas import ShipmentCreate, ShipmentOut

router = APIRouter(prefix="/shipments", tags=["Module 33: Shipping Order Management"])

@router.post("", response_model=ResponseSchema[ShipmentOut])
def create_shipment(
    data: ShipmentCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == data.order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    existing_shipment = db.query(Shipment).filter(Shipment.order_id == data.order_id).first()
    if existing_shipment:
        raise BadRequestError("Shipment already exists for this order")

    carrier_info = shipping_provider.create_shipment(order_id=order.id, carrier=data.carrier)

    shipment = Shipment(
        order_id=order.id,
        carrier=carrier_info["carrier"],
        tracking_number=carrier_info["tracking_number"],
        shipping_label_url=carrier_info["label_url"],
        status=ShipmentStatus.PENDING
    )
    db.add(shipment)
    db.flush()

    # Create initial delivery assignment
    assignment = DeliveryAssignment(shipment_id=shipment.id)
    db.add(assignment)

    # Initial tracking event
    initial_event = ShipmentTrackingEvent(
        shipment_id=shipment.id,
        status=ShipmentStatus.PENDING,
        location="Warehouse Dispatch Hub",
        description="Shipment label created. Ready for carrier pickup."
    )
    db.add(initial_event)
    db.commit()
    db.refresh(shipment)

    log_audit(db, AuditAction.CREATE, "Shipment", str(shipment.id), current_user.id, new_values={"tracking_number": shipment.tracking_number})
    return ResponseSchema(message="Shipment created successfully", data=ShipmentOut.model_validate(shipment))

@router.get("/order/{order_id}", response_model=ResponseSchema[ShipmentOut])
def get_shipment_by_order(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(Shipment.order_id == order_id).first()
    if not shipment:
        raise NotFoundError("Shipment not found for this order")
    return ResponseSchema(data=ShipmentOut.model_validate(shipment))
