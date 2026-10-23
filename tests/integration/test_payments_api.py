from app.models.orders import Order
from app.models.payments import Payment
from app.common.enums import OrderStatus, PaymentStatus

def test_process_payment_flow(client, customer_headers, customer_user, db):
    order = Order(
        order_number="ORD-PAY-TEST",
        user_id=customer_user.id,
        subtotal_amount=50.0,
        discount_amount=0.0,
        tax_amount=4.0,
        shipping_amount=5.0,
        total_amount=59.0,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.flush()

    payment = Payment(
        order_id=order.id,
        amount=59.0,
        status=PaymentStatus.PENDING
    )
    db.add(payment)
    db.commit()

    resp = client.post("/api/v1/payments/process", json={
        "order_id": order.id,
        "payment_method": "stripe",
        "idempotency_key": "test_idem_key_123"
    }, headers=customer_headers)

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "successful"
