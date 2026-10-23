from app.models.orders import Order
from app.common.enums import OrderStatus

def test_orders_retrieval(client, customer_headers, customer_user, db):
    # Create order
    order = Order(
        order_number="ORD-TEST-12345",
        user_id=customer_user.id,
        subtotal_amount=100.0,
        discount_amount=0.0,
        tax_amount=8.0,
        shipping_amount=10.0,
        total_amount=118.0,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.commit()

    resp = client.get("/api/v1/orders", headers=customer_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert any(o["order_number"] == "ORD-TEST-12345" for o in data["items"])
