from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.logistics import DeliveryAssignment, Shipment, ShipmentTrackingEvent
from app.models.orders import Order
from app.models.users import User
from app.common.responses import ResponseSchema
from app.common.dependencies import require_roles
from app.common.enums import UserRole, ShipmentStatus, OrderStatus
from app.core.exceptions import NotFoundError, BadRequestError
from app.modules.deliveries.schemas import DeliveryAssignmentCreate, DeliveryAttemptRecord, DeliveryAssignmentOut

router = APIRouter(prefix="/deliveries", tags=["Module 35: Delivery Management"])

@router.post("/assign", response_model=ResponseSchema[DeliveryAssignmentOut])
def assign_delivery_person(
    data: DeliveryAssignmentCreate,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.shipment_id == data.shipment_id).first()
    if not assignment:
        assignment = DeliveryAssignment(shipment_id=data.shipment_id)
        db.add(assignment)

    assignment.delivery_person_id = data.delivery_person_id
    db.commit()
    db.refresh(assignment)
    return ResponseSchema(message="Delivery personnel assigned", data=DeliveryAssignmentOut.model_validate(assignment))

@router.post("/{shipment_id}/attempt", response_model=ResponseSchema[DeliveryAssignmentOut])
def record_delivery_attempt(
    shipment_id: int,
    data: DeliveryAttemptRecord,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    shipment = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not shipment:
        raise NotFoundError("Shipment not found")

    assignment = db.query(DeliveryAssignment).filter(DeliveryAssignment.shipment_id == shipment_id).first()
    if not assignment:
        assignment = DeliveryAssignment(shipment_id=shipment_id)
        db.add(assignment)

    assignment.attempts_count += 1

    if data.is_successful:
        assignment.confirmation_signature = data.confirmation_signature
        assignment.proof_of_delivery_url = data.proof_of_delivery_url
        shipment.status = ShipmentStatus.DELIVERED
        shipment.delivered_at = datetime.now(timezone.utc)

        order = db.query(Order).filter(Order.id == shipment.order_id).first()
        if order:
            order.status = OrderStatus.DELIVERED

        event = ShipmentTrackingEvent(
            shipment_id=shipment.id,
            status=ShipmentStatus.DELIVERED,
            location="Customer Address",
            description="Delivered and signed by recipient"
        )
        db.add(event)
    else:
        assignment.failure_reason = data.failure_reason
        if assignment.attempts_count >= assignment.max_attempts:
            shipment.status = ShipmentStatus.FAILED
        event = ShipmentTrackingEvent(
            shipment_id=shipment.id,
            status=ShipmentStatus.FAILED if assignment.attempts_count >= assignment.max_attempts else shipment.status,
            location="Delivery Route",
            description=f"Delivery attempt #{assignment.attempts_count} failed: {data.failure_reason}"
        )
        db.add(event)

    db.commit()
    db.refresh(assignment)
    return ResponseSchema(message="Delivery attempt recorded", data=DeliveryAssignmentOut.model_validate(assignment))
