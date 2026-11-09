import pytest
from app.models.orders import Order, OrderItem
from app.models.payments import Payment
from app.models.inventory import InventoryItem
from app.common.enums import OrderStatus, PaymentStatus

def test_split_shipment_workflow(client, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    wh = sample_catalog["warehouse"]

    order = Order(
        order_number="ORD-SPLIT-001",
        user_id=1,
        subtotal_amount=1800.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=1800.0,
        status=OrderStatus.CONFIRMED
    )
    db.add(order)
    db.flush()

    item1 = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        unit_price=900.0,
        quantity=2,
        fulfilled_quantity=0,
        cancelled_quantity=0,
        total_price=1800.0,
        fulfillment_status="PENDING"
    )
    db.add(item1)
    db.commit()

    # Split shipment 1: Fulfill 1 unit out of 2
    res1 = client.post(
        f"/api/v1/orders/{order.id}/split-shipment",
        json={
            "carrier": "FedEx",
            "items": [{"order_item_id": item1.id, "quantity": 1}]
        },
        headers=superadmin_headers
    )
    assert res1.status_code == 200
    data1 = res1.json()["data"]
    assert data1["carrier"] == "FedEx"
    assert data1["items"][0]["fulfillment_status"] == "PARTIALLY_FULFILLED"

    # Verify order is PROCESSING (partially fulfilled)
    ord_check = client.get(f"/api/v1/orders/{order.id}", headers=superadmin_headers)
    assert ord_check.json()["data"]["status"] == "processing"

    # Split shipment 2: Fulfill remaining 1 unit
    res2 = client.post(
        f"/api/v1/orders/{order.id}/split-shipment",
        json={
            "carrier": "DHL",
            "items": [{"order_item_id": item1.id, "quantity": 1}]
        },
        headers=superadmin_headers
    )
    assert res2.status_code == 200
    data2 = res2.json()["data"]
    assert data2["items"][0]["fulfillment_status"] == "FULFILLED"

    # Verify order status transitioned to SHIPPED
    ord_check2 = client.get(f"/api/v1/orders/{order.id}", headers=superadmin_headers)
    assert ord_check2.json()["data"]["status"] == "shipped"


def test_item_cancellation_and_inventory_release(client, customer_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    wh = sample_catalog["warehouse"]
    inv = sample_catalog["inventory"]
    initial_reserved = inv.reserved_quantity

    order = Order(
        order_number="ORD-CANCEL-ITEM-001",
        user_id=1,
        subtotal_amount=1800.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=1800.0,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        unit_price=900.0,
        quantity=2,
        fulfilled_quantity=0,
        cancelled_quantity=0,
        total_price=1800.0,
        fulfillment_status="PENDING"
    )
    db.add(item)
    inv.reserved_quantity += 2
    db.commit()

    # Get customer id
    prof = client.get("/api/v1/profile", headers=customer_headers).json()["data"]
    order.user_id = prof["user_id"]
    db.commit()

    # Cancel 1 unit of the item
    res = client.post(
        f"/api/v1/orders/{order.id}/cancel-item",
        json={"order_item_id": item.id, "quantity": 1, "reason": "Accidental double quantity"},
        headers=customer_headers
    )
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["cancelled_quantity"] == 1
    assert data["refund_amount"] == 900.0

    db.refresh(inv)
    assert inv.reserved_quantity == initial_reserved + 1


def test_backorder_and_admin_update(client, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    order = Order(
        order_number="ORD-BO-001",
        user_id=1,
        subtotal_amount=900.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=900.0,
        status=OrderStatus.CONFIRMED
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        unit_price=900.0,
        quantity=1,
        total_price=900.0,
        fulfillment_status="PENDING"
    )
    db.add(item)
    db.commit()

    # Backorder item
    bo_res = client.post(
        f"/api/v1/orders/{order.id}/backorder-item",
        json={"order_item_id": item.id, "notes": "Awaiting supplier restock shipment"},
        headers=superadmin_headers
    )
    assert bo_res.status_code == 200
    assert bo_res.json()["data"]["fulfillment_status"] == "BACKORDERED"

    # Admin update
    adm_res = client.put(
        f"/api/v1/orders/{order.id}/admin-update",
        json={"notes": "Priority VIP order with backorder escalation"},
        headers=superadmin_headers
    )
    assert adm_res.status_code == 200
    assert "VIP" in adm_res.json()["data"]["notes"]


def test_order_timeline_and_fulfillment_details(client, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    order = Order(
        order_number="ORD-TIME-001",
        user_id=1,
        subtotal_amount=900.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=900.0,
        status=OrderStatus.CONFIRMED
    )
    db.add(order)
    db.flush()

    item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        unit_price=900.0,
        quantity=1,
        total_price=900.0,
        fulfillment_status="PENDING"
    )
    db.add(item)
    db.commit()

    # Timeline check
    timeline_res = client.get(f"/api/v1/orders/{order.id}/timeline", headers=superadmin_headers)
    assert timeline_res.status_code == 200
    events = timeline_res.json()["data"]["events"]
    assert len(events) >= 1
    assert events[0]["event_type"] == "ORDER_PLACED"

    # Fulfillment details check
    fulf_res = client.get(f"/api/v1/orders/{order.id}/fulfillment", headers=superadmin_headers)
    assert fulf_res.status_code == 200
    fulf_data = fulf_res.json()["data"]
    assert fulf_data["fulfillment_percentage"] == 0.0
    assert len(fulf_data["items"]) == 1
    assert fulf_data["items"][0]["sku"] == prod.sku
