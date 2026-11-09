import pytest
from datetime import datetime, timezone, timedelta
from app.models.orders import Order, OrderItem
from app.models.payments import Payment
from app.common.enums import OrderStatus, PaymentStatus, WarrantyStatus

def test_return_inspection_and_warranty(client, customer_headers, superadmin_headers, sample_catalog, db):
    prod = sample_catalog["product"]
    wh = sample_catalog["warehouse"]

    # Customer user id
    prof = client.get("/api/v1/profile", headers=customer_headers).json()["data"]
    cust_id = prof["user_id"]

    order = Order(
        order_number="ORD-RET-INSP-001",
        user_id=cust_id,
        subtotal_amount=900.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=900.0,
        status=OrderStatus.DELIVERED
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
        fulfillment_status="DELIVERED"
    )
    db.add(item)

    payment = Payment(
        order_id=order.id,
        amount=900.0,
        status=PaymentStatus.SUCCESSFUL,
        transaction_ref="pi_insp_test_001"
    )
    db.add(payment)
    db.commit()

    # 1. Customer creates return request with evidence url
    ret_resp = client.post(
        "/api/v1/returns",
        json={
            "order_id": order.id,
            "reason": "Wrong item delivered",
            "evidence_url": "https://storage.shopsphere.com/evidence/photo_01.jpg",
            "items": [{"order_item_id": item.id, "quantity": 1, "condition": "UNOPENED"}]
        },
        headers=customer_headers
    )
    assert ret_resp.status_code == 200
    ret_id = ret_resp.json()["data"]["id"]
    assert ret_resp.json()["data"]["evidence_url"] == "https://storage.shopsphere.com/evidence/photo_01.jpg"

    # 2. Staff inspects return with outcome RESTOCKABLE and auto_issue_refund True
    insp_resp = client.post(
        f"/api/v1/returns/{ret_id}/inspect",
        json={
            "outcome": "RESTOCKABLE",
            "notes": "Item brand new in sealed box; eligible for restocking",
            "auto_issue_refund": True
        },
        headers=superadmin_headers
    )
    assert insp_resp.status_code == 200
    assert insp_resp.json()["data"]["inspection_outcome"] == "RESTOCKABLE"
    assert insp_resp.json()["data"]["status"] == "completed"

    # 3. Customer submits Warranty Claim
    war_resp = client.post(
        "/api/v1/warranty/claims",
        json={
            "order_item_id": item.id,
            "product_id": prod.id,
            "claim_reason": "Motherboard component failure after 2 months",
            "description": "Laptop shuts down randomly during high CPU usage",
            "evidence_url": "https://storage.shopsphere.com/diagnostics.pdf"
        },
        headers=customer_headers
    )
    assert war_resp.status_code == 200
    war_id = war_resp.json()["data"]["id"]
    assert war_resp.json()["data"]["status"] == "PENDING"

    # 4. Support agent reviews and approves replacement
    rev_resp = client.put(
        f"/api/v1/warranty/claims/{war_id}/review",
        json={
            "status": WarrantyStatus.REPLACED,
            "resolution_notes": "Diagnostic confirmed hardware defect. Free replacement device authorized."
        },
        headers=superadmin_headers
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["data"]["status"] == "REPLACED"
