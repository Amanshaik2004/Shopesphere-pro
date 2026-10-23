from app.models.orders import Order, OrderItem
from app.models.payments import Payment
from app.models.inventory import InventoryItem
from app.common.enums import OrderStatus, PaymentStatus

def test_return_and_refund_lifecycle(client, customer_headers, superadmin_headers, sample_catalog, db):
    # Setup delivered order and payment
    prod = sample_catalog["product"]
    wh = sample_catalog["warehouse"]

    order = Order(
        order_number="ORD-RET-TEST-001",
        user_id=1,  # will be customer user id
        subtotal_amount=900.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=900.0,
        status=OrderStatus.DELIVERED
    )
    db.add(order)
    db.flush()

    order_item = OrderItem(
        order_id=order.id,
        product_id=prod.id,
        product_name=prod.name,
        sku=prod.sku,
        unit_price=900.0,
        quantity=1,
        total_price=900.0,
        fulfillment_status="DELIVERED"
    )
    db.add(order_item)

    payment = Payment(
        order_id=order.id,
        amount=900.0,
        status=PaymentStatus.SUCCESSFUL,
        transaction_ref="pi_test_return_001"
    )
    db.add(payment)
    db.commit()

    # 1. Customer requests return
    # Fetch current customer id
    prof_resp = client.get("/api/v1/profile", headers=customer_headers)
    cust_id = prof_resp.json()["data"]["user_id"]
    order.user_id = cust_id
    db.commit()

    ret_resp = client.post("/api/v1/returns", json={
        "order_id": order.id,
        "reason": "Defective screen upon arrival",
        "items": [{"order_item_id": order_item.id, "quantity": 1, "condition": "OPENED"}]
    }, headers=customer_headers)
    assert ret_resp.status_code == 200
    ret_data = ret_resp.json()["data"]
    return_id = ret_data["id"]

    # 2. Staff approves return
    appr_resp = client.put(f"/api/v1/returns/{return_id}/review", json={
        "is_approved": True,
        "refund_amount": 900.0
    }, headers=superadmin_headers)
    assert appr_resp.status_code == 200
    assert appr_resp.json()["data"]["status"] == "approved"

    # 3. Warehouse receives return & restocks
    recv_resp = client.post(f"/api/v1/returns/{return_id}/receive?warehouse_id={wh.id}", headers=superadmin_headers)
    assert recv_resp.status_code == 200
    assert recv_resp.json()["data"]["status"] == "completed"

    # 4. Finance issues refund
    ref_resp = client.post("/api/v1/refunds", json={
        "order_id": order.id,
        "amount": 900.0,
        "reason": "Return completed for defective product"
    }, headers=superadmin_headers)
    assert ref_resp.status_code == 200
    assert ref_resp.json()["data"]["status"] == "successful"
