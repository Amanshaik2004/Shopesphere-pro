import pytest
from app.models.orders import Order
from app.models.payments import Payment, PaymentTransaction, PaymentExceptionLog
from app.common.enums import OrderStatus, PaymentStatus

def test_payment_reconciliation(client, finance_headers, db):
    order = Order(
        order_number="ORD-PAY-REC-001",
        user_id=1,
        subtotal_amount=500.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=500.0,
        status=OrderStatus.CONFIRMED
    )
    db.add(order)
    db.flush()

    payment = Payment(
        order_id=order.id,
        amount=500.0,
        status=PaymentStatus.SUCCESSFUL,
        transaction_ref="pi_reconcile_test_123",
        reconciled=False
    )
    db.add(payment)
    db.commit()

    rec_res = client.post(f"/api/v1/payments/{payment.id}/reconcile", headers=finance_headers)
    assert rec_res.status_code == 200
    data = rec_res.json()["data"]
    assert data["reconciled"] is True
    assert data["is_matched"] is True

    db.refresh(payment)
    assert payment.reconciled is True


def test_payment_callbacks_and_idempotency(client, db):
    order = Order(
        order_number="ORD-CB-001",
        user_id=1,
        subtotal_amount=300.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=300.0,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.flush()

    payment = Payment(
        order_id=order.id,
        amount=300.0,
        status=PaymentStatus.PENDING,
        transaction_ref="pi_callback_test_999"
    )
    db.add(payment)
    db.commit()

    # 1. Successful callback
    cb1 = client.post(
        "/api/v1/payments/callback",
        json={
            "event_type": "payment.success",
            "transaction_ref": "pi_callback_test_999",
            "idempotency_key": "idemp_cb_key_001",
            "status": "succeeded",
            "amount": 300.0
        }
    )
    assert cb1.status_code == 200
    assert cb1.json()["data"]["status"] == "success"

    db.refresh(payment)
    assert payment.status == PaymentStatus.SUCCESSFUL

    # 2. Duplicate callback with same idempotency key
    cb2 = client.post(
        "/api/v1/payments/callback",
        json={
            "event_type": "payment.success",
            "transaction_ref": "pi_callback_test_999",
            "idempotency_key": "idemp_cb_key_001",
            "status": "succeeded",
            "amount": 300.0
        }
    )
    assert cb2.status_code == 200
    assert cb2.json()["data"]["status"] == "duplicate_handled"


def test_payment_exception_logging_and_resolution(client, finance_headers, db):
    order = Order(
        order_number="ORD-PAY-EXC-001",
        user_id=1,
        subtotal_amount=250.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=250.0,
        status=OrderStatus.PENDING
    )
    db.add(order)
    db.flush()

    payment = Payment(
        order_id=order.id,
        amount=250.0,
        status=PaymentStatus.PENDING,
        transaction_ref="pi_timeout_test_777"
    )
    db.add(payment)
    db.commit()

    # Callback reports timeout
    client.post(
        "/api/v1/payments/callback",
        json={
            "event_type": "payment.timeout",
            "transaction_ref": "pi_timeout_test_777",
            "status": "timeout",
            "reason": "Gateway timed out waiting for cardholder approval"
        }
    )

    # List exceptions
    exc_res = client.get("/api/v1/payments/exceptions?status=UNRESOLVED", headers=finance_headers)
    assert exc_res.status_code == 200
    exceptions = exc_res.json()["data"]
    match = next((e for e in exceptions if e["payment_id"] == payment.id), None)
    assert match is not None
    assert match["exception_type"] == "TIMEOUT"

    # Resolve exception
    resolve_res = client.put(
        f"/api/v1/payments/{payment.id}/resolve-exception",
        json={"resolution_notes": "Customer retried payment via COD; marked resolved"},
        headers=finance_headers
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["data"]["status"] == "RESOLVED"


def test_partial_refunds_and_idempotency(client, finance_headers, db):
    order = Order(
        order_number="ORD-MULTI-REF-001",
        user_id=1,
        subtotal_amount=400.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=400.0,
        status=OrderStatus.CONFIRMED
    )
    db.add(order)
    db.flush()

    payment = Payment(
        order_id=order.id,
        amount=400.0,
        status=PaymentStatus.SUCCESSFUL,
        transaction_ref="pi_multi_ref_001"
    )
    db.add(payment)
    db.commit()

    # Partial refund 1: $150 with idempotency key
    r1 = client.post(
        "/api/v1/refunds",
        json={"order_id": order.id, "amount": 150.0, "reason": "Customer damaged box", "idempotency_key": "ref_idem_001"},
        headers=finance_headers
    )
    assert r1.status_code == 200
    assert r1.json()["data"]["amount"] == 150.0

    # Duplicate call with same idempotency key returns existing refund
    r1_dup = client.post(
        "/api/v1/refunds",
        json={"order_id": order.id, "amount": 150.0, "reason": "Customer damaged box", "idempotency_key": "ref_idem_001"},
        headers=finance_headers
    )
    assert r1_dup.status_code == 200
    assert "idempotent" in r1_dup.json()["message"]

    # Partial refund 2: $200
    r2 = client.post(
        "/api/v1/refunds",
        json={"order_id": order.id, "amount": 200.0, "reason": "Partial dissatisfaction"},
        headers=finance_headers
    )
    assert r2.status_code == 200
    assert r2.json()["data"]["amount"] == 200.0

    # Refund 3: Exceeds remaining $50 refundable balance -> returns 400
    r3 = client.post(
        "/api/v1/refunds",
        json={"order_id": order.id, "amount": 100.0, "reason": "Excess amount"},
        headers=finance_headers
    )
    assert r3.status_code == 400
