import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.orders import Order, OrderItem, OrderStatusHistory
from app.models.logistics import Shipment, ShipmentItem, ShipmentTrackingEvent
from app.models.payments import Payment, Refund, PaymentTransaction
from app.models.inventory import InventoryItem, InventoryMovement
from app.models.users import User
from app.common.responses import ResponseSchema, MessageResponse
from app.common.pagination import PaginationParams, PaginatedResponse, PaginatedData, paginate_query
from app.common.dependencies import get_current_active_user, require_roles
from app.common.enums import UserRole, OrderStatus, ShipmentStatus, PaymentStatus, AuditAction
from app.core.exceptions import NotFoundError, ForbiddenError, BadRequestError
from app.core.audit import log_audit
from app.modules.orders.schemas import (
    OrderOut, OrderItemOut, SplitShipmentRequest, SplitShipmentResponse,
    ItemCancelRequest, ItemCancelResponse, BackorderItemRequest,
    OrderTimelineResponse, OrderTimelineEvent, OrderFulfillmentDetailsResponse,
    ItemFulfillmentDetail, AdminOrderUpdateRequest
)

router = APIRouter(prefix="/orders", tags=["Module 25: Order Management"])

@router.get("", response_model=PaginatedResponse[OrderOut])
def get_orders(
    status: Optional[OrderStatus] = Query(None),
    order_number: Optional[str] = Query(None),
    pagination: PaginationParams = Depends(),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    query = db.query(Order)
    if current_user.role == UserRole.CUSTOMER:
        query = query.filter(Order.user_id == current_user.id)
    
    if status:
        query = query.filter(Order.status == status)
    if order_number:
        query = query.filter(Order.order_number.ilike(f"%{order_number}%"))

    query = query.order_by(Order.created_at.desc())
    paginated = paginate_query(query, pagination)

    return PaginatedResponse(
        message="Orders retrieved successfully",
        data=PaginatedData(
            items=[OrderOut.model_validate(o) for o in paginated.items],
            total=paginated.total,
            page=paginated.page,
            page_size=paginated.page_size,
            total_pages=paginated.total_pages
        )
    )

@router.get("/{order_id}", response_model=ResponseSchema[OrderOut])
def get_order_by_id(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("You do not have permission to view this order")

    return ResponseSchema(data=OrderOut.model_validate(order))


# =========================================================================
# Phase 2: Advanced Order Management Endpoints
# =========================================================================

@router.post("/{order_id}/split-shipment", response_model=ResponseSchema[SplitShipmentResponse])
def create_split_shipment(
    order_id: int,
    data: SplitShipmentRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER, UserRole.DELIVERY_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if order.status in [OrderStatus.CANCELLED, OrderStatus.DELIVERED]:
        raise BadRequestError(f"Cannot fulfill order in {order.status.value} status")

    if not data.items:
        raise BadRequestError("At least one item must be included in the split shipment")

    tracking = data.tracking_number or f"TRK-{uuid.uuid4().hex[:10].upper()}"
    shipment = Shipment(
        order_id=order.id,
        carrier=data.carrier,
        tracking_number=tracking,
        status=ShipmentStatus.DISPATCHED,
        shipped_at=datetime.now(timezone.utc)
    )
    db.add(shipment)
    db.flush()

    shipped_item_records = []
    for split_item in data.items:
        item = db.query(OrderItem).filter(OrderItem.id == split_item.order_item_id, OrderItem.order_id == order.id).first()
        if not item:
            raise NotFoundError(f"Order item {split_item.order_item_id} does not belong to this order")

        remaining_unfulfilled = item.quantity - item.fulfilled_quantity - item.cancelled_quantity
        if split_item.quantity > remaining_unfulfilled:
            raise BadRequestError(
                f"Requested quantity {split_item.quantity} exceeds unfulfilled quantity {remaining_unfulfilled} for SKU {item.sku}"
            )

        item.fulfilled_quantity += split_item.quantity
        if item.fulfilled_quantity + item.cancelled_quantity >= item.quantity:
            item.fulfillment_status = "FULFILLED"
        else:
            item.fulfillment_status = "PARTIALLY_FULFILLED"

        ship_item = ShipmentItem(
            shipment_id=shipment.id,
            order_item_id=item.id,
            quantity=split_item.quantity
        )
        db.add(ship_item)
        shipped_item_records.append({
            "order_item_id": item.id,
            "sku": item.sku,
            "quantity": split_item.quantity,
            "fulfillment_status": item.fulfillment_status
        })

    # Check overall order status
    all_fulfilled = all(
        (i.fulfilled_quantity + i.cancelled_quantity) >= i.quantity
        for i in order.items
    )
    from_status = order.status
    if all_fulfilled:
        order.status = OrderStatus.SHIPPED
    else:
        order.status = OrderStatus.PROCESSING

    history = OrderStatusHistory(
        order_id=order.id,
        from_status=from_status,
        to_status=order.status,
        changed_by_id=current_user.id,
        actor_role=current_user.role.value,
        comment=f"Split shipment {tracking} dispatched with {len(data.items)} items"
    )
    db.add(history)
    db.commit()
    db.refresh(shipment)

    log_audit(db, AuditAction.STATUS_CHANGE, "Order", str(order.id), current_user.id, new_values={"split_shipment": tracking, "status": order.status.value})

    return ResponseSchema(
        message="Split shipment created and items updated successfully",
        data=SplitShipmentResponse(
            shipment_id=shipment.id,
            tracking_number=shipment.tracking_number,
            carrier=shipment.carrier,
            status=shipment.status.value,
            order_id=order.id,
            items=shipped_item_records
        )
    )


@router.post("/{order_id}/cancel-item", response_model=ResponseSchema[ItemCancelResponse])
def cancel_order_item(
    order_id: int,
    data: ItemCancelRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED, OrderStatus.CANCELLED]:
        raise BadRequestError(f"Cannot cancel items in {order.status.value} status")

    item = db.query(OrderItem).filter(OrderItem.id == data.order_item_id, OrderItem.order_id == order.id).first()
    if not item:
        raise NotFoundError("Order item not found in this order")

    available_to_cancel = item.quantity - item.fulfilled_quantity - item.cancelled_quantity
    if data.quantity > available_to_cancel:
        raise BadRequestError(f"Cannot cancel {data.quantity} units; only {available_to_cancel} available to cancel")

    item.cancelled_quantity += data.quantity
    if item.cancelled_quantity >= item.quantity:
        item.fulfillment_status = "CANCELLED"
    else:
        item.fulfillment_status = "PARTIALLY_CANCELLED"

    # Release reserved stock for cancelled quantity
    inv = db.query(InventoryItem).filter(
        InventoryItem.product_id == item.product_id,
        InventoryItem.variant_id == item.variant_id
    ).first()
    if inv:
        released = min(inv.reserved_quantity, data.quantity)
        inv.reserved_quantity -= released
        movement = InventoryMovement(
            inventory_item_id=inv.id,
            movement_type="RELEASE",
            quantity=released,
            reference_type="ITEM_CANCELLATION",
            note=f"Cancelled {data.quantity} units of SKU {item.sku} in order {order.order_number}"
        )
        db.add(movement)

    refund_amount = round(float(item.unit_price) * data.quantity, 2)
    # Check if payment was made; if so, record a pending/successful refund record
    payment = db.query(Payment).filter(Payment.order_id == order.id, Payment.status == PaymentStatus.SUCCESSFUL).first()
    if payment:
        refund = Refund(
            payment_id=payment.id,
            order_id=order.id,
            amount=refund_amount,
            reason=f"Item cancellation: {data.reason}",
            status=PaymentStatus.PENDING,
            processed_by_id=current_user.id
        )
        db.add(refund)

    # If all items are cancelled, cancel entire order
    all_cancelled = all((i.cancelled_quantity >= i.quantity) for i in order.items)
    from_status = order.status
    if all_cancelled:
        order.status = OrderStatus.CANCELLED

    history = OrderStatusHistory(
        order_id=order.id,
        from_status=from_status,
        to_status=order.status,
        changed_by_id=current_user.id,
        actor_role=current_user.role.value,
        comment=f"Cancelled {data.quantity}x {item.sku}: {data.reason}"
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    log_audit(db, AuditAction.STATUS_CHANGE, "OrderItem", str(item.id), current_user.id, new_values={"cancelled_quantity": item.cancelled_quantity, "reason": data.reason})

    return ResponseSchema(
        message=f"Successfully cancelled {data.quantity} units of {item.sku}",
        data=ItemCancelResponse(
            order_id=order.id,
            order_item_id=item.id,
            cancelled_quantity=data.quantity,
            refund_amount=refund_amount,
            order_status=order.status
        )
    )


@router.post("/{order_id}/backorder-item", response_model=ResponseSchema[OrderItemOut])
def backorder_order_item(
    order_id: int,
    data: BackorderItemRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    item = db.query(OrderItem).filter(OrderItem.id == data.order_item_id, OrderItem.order_id == order.id).first()
    if not item:
        raise NotFoundError("Order item not found")

    item.fulfillment_status = "BACKORDERED"
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=order.status,
        to_status=order.status,
        changed_by_id=current_user.id,
        actor_role=current_user.role.value,
        comment=f"Item {item.sku} placed on backorder: {data.notes}"
    )
    db.add(history)
    db.commit()
    db.refresh(item)
    return ResponseSchema(message=f"Item {item.sku} placed on backorder", data=OrderItemOut.model_validate(item))


@router.post("/{order_id}/complete-partial", response_model=ResponseSchema[OrderOut])
def complete_partial_order(
    order_id: int,
    notes: Optional[str] = Query("Completed with remaining items cancelled/unfulfillable"),
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    from_st = order.status
    order.status = OrderStatus.DELIVERED
    history = OrderStatusHistory(
        order_id=order.id,
        from_status=from_st,
        to_status=OrderStatus.DELIVERED,
        changed_by_id=current_user.id,
        actor_role=current_user.role.value,
        comment=f"Partial order marked complete: {notes}"
    )
    db.add(history)
    db.commit()
    db.refresh(order)
    return ResponseSchema(message="Partial order marked completed", data=OrderOut.model_validate(order))


@router.get("/{order_id}/timeline", response_model=ResponseSchema[OrderTimelineResponse])
def get_order_timeline(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    events: List[OrderTimelineEvent] = []

    # 1. Order Placed
    events.append(OrderTimelineEvent(
        event_type="ORDER_PLACED",
        timestamp=order.created_at,
        description=f"Order {order.order_number} placed for total amount ${order.total_amount}",
        actor=f"User #{order.user_id}"
    ))

    # 2. Status History
    for hist in order.status_history:
        actor_label = f"User #{hist.changed_by_id}" if hist.changed_by_id else "System"
        if hist.actor_role:
            actor_label += f" ({hist.actor_role})"
        events.append(OrderTimelineEvent(
            event_type="STATUS_CHANGE",
            timestamp=hist.created_at,
            description=f"Status changed to {hist.to_status.value}: {hist.comment or ''}",
            actor=actor_label
        ))

    # 3. Payments
    payments = db.query(Payment).filter(Payment.order_id == order.id).all()
    for pay in payments:
        events.append(OrderTimelineEvent(
            event_type="PAYMENT",
            timestamp=pay.created_at,
            description=f"Payment of ${pay.amount} ({pay.payment_method.value}) - status: {pay.status.value}",
            details={"transaction_ref": pay.transaction_ref, "reconciled": pay.reconciled}
        ))

    # 4. Shipments
    shipments = db.query(Shipment).filter(Shipment.order_id == order.id).all()
    for ship in shipments:
        events.append(OrderTimelineEvent(
            event_type="SHIPMENT_DISPATCHED",
            timestamp=ship.created_at,
            description=f"Shipment {ship.tracking_number} with carrier {ship.carrier} ({ship.status.value})",
            details={"tracking_number": ship.tracking_number, "carrier": ship.carrier}
        ))
        for evt in ship.tracking_events:
            events.append(OrderTimelineEvent(
                event_type="TRACKING_EVENT",
                timestamp=evt.event_time,
                description=f"{evt.status.value} at {evt.location}: {evt.description}",
                details={"tracking_number": ship.tracking_number}
            ))

    # 5. Refunds
    refunds = db.query(Refund).filter(Refund.order_id == order.id).all()
    for ref in refunds:
        events.append(OrderTimelineEvent(
            event_type="REFUND",
            timestamp=ref.created_at,
            description=f"Refund of ${ref.amount} - reason: {ref.reason} ({ref.status.value})"
        ))

    events.sort(key=lambda e: e.timestamp)

    return ResponseSchema(
        data=OrderTimelineResponse(
            order_id=order.id,
            order_number=order.order_number,
            events=events
        )
    )


@router.get("/{order_id}/fulfillment", response_model=ResponseSchema[OrderFulfillmentDetailsResponse])
def get_order_fulfillment_details(
    order_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    if current_user.role == UserRole.CUSTOMER and order.user_id != current_user.id:
        raise ForbiddenError("Access denied")

    item_details = []
    total_qty = 0
    total_fulfilled = 0
    for i in order.items:
        pending = max(0, i.quantity - i.fulfilled_quantity - i.cancelled_quantity)
        item_details.append(ItemFulfillmentDetail(
            order_item_id=i.id,
            product_name=i.product_name,
            sku=i.sku,
            ordered_quantity=i.quantity,
            fulfilled_quantity=i.fulfilled_quantity,
            cancelled_quantity=i.cancelled_quantity,
            pending_quantity=pending,
            fulfillment_status=i.fulfillment_status
        ))
        total_qty += i.quantity
        total_fulfilled += i.fulfilled_quantity

    percentage = round((total_fulfilled / total_qty * 100), 2) if total_qty > 0 else 0.0
    shipments_count = db.query(Shipment).filter(Shipment.order_id == order.id).count()

    return ResponseSchema(
        data=OrderFulfillmentDetailsResponse(
            order_id=order.id,
            order_number=order.order_number,
            order_status=order.status,
            fulfillment_percentage=percentage,
            items=item_details,
            shipments_count=shipments_count
        )
    )


@router.put("/{order_id}/admin-update", response_model=ResponseSchema[OrderOut])
def admin_update_order(
    order_id: int,
    data: AdminOrderUpdateRequest,
    current_user: User = Depends(require_roles(UserRole.SUPER_ADMIN, UserRole.ADMIN, UserRole.ORDER_MANAGER)),
    db: Session = Depends(get_db)
):
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise NotFoundError("Order not found")

    old_vals = {}
    new_vals = {}
    if data.shipping_address_id is not None:
        old_vals["shipping_address_id"] = order.shipping_address_id
        order.shipping_address_id = data.shipping_address_id
        new_vals["shipping_address_id"] = data.shipping_address_id

    if data.billing_address_id is not None:
        old_vals["billing_address_id"] = order.billing_address_id
        order.billing_address_id = data.billing_address_id
        new_vals["billing_address_id"] = data.billing_address_id

    if data.notes is not None:
        old_vals["notes"] = order.notes
        order.notes = data.notes
        new_vals["notes"] = data.notes

    if data.status is not None:
        old_vals["status"] = order.status.value
        from_st = order.status
        order.status = data.status
        new_vals["status"] = data.status.value
        history = OrderStatusHistory(
            order_id=order.id,
            from_status=from_st,
            to_status=data.status,
            changed_by_id=current_user.id,
            actor_role=current_user.role.value,
            comment=f"Administrative status update to {data.status.value}"
        )
        db.add(history)

    db.commit()
    db.refresh(order)
    log_audit(db, AuditAction.UPDATE, "Order", str(order.id), current_user.id, old_values=old_vals, new_values=new_vals)

    return ResponseSchema(message="Order updated administratively", data=OrderOut.model_validate(order))
