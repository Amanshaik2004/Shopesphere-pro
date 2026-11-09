import pytest
from app.models.orders import Order
from app.models.loyalty import LoyaltyAccount, LoyaltyRule
from app.common.enums import OrderStatus, LoyaltyTier

def test_loyalty_earning_redemption_and_reversal(client, customer_headers, superadmin_headers, db):
    # 1. Create Loyalty Rule: 1 point per $1 spent, 100 points = $1 discount, min 50 to redeem
    rule_res = client.post(
        "/api/v1/loyalty/rules",
        json={
            "name": "Standard Points Program",
            "points_per_dollar": 1.0,
            "redemption_rate": 100.0,
            "min_points_to_redeem": 50,
            "points_expiry_days": 365
        },
        headers=superadmin_headers
    )
    assert rule_res.status_code == 200

    # Get customer id
    prof = client.get("/api/v1/profile", headers=customer_headers).json()["data"]
    cust_id = prof["user_id"]

    # 2. Check initial balance
    bal_res = client.get("/api/v1/loyalty/me/balance", headers=customer_headers)
    assert bal_res.status_code == 200
    assert bal_res.json()["data"]["points_balance"] == 0

    # 3. Simulate completed order of $600 and credit points
    order = Order(
        order_number="ORD-LOYAL-001",
        user_id=cust_id,
        subtotal_amount=600.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=600.0,
        status=OrderStatus.DELIVERED
    )
    db.add(order)
    db.commit()

    credit_res = client.post(f"/api/v1/loyalty/credit-order/{order.id}", headers=superadmin_headers)
    assert credit_res.status_code == 200
    assert credit_res.json()["data"]["credited_points"] == 600

    # Customer should now have 600 points and SILVER tier (>= 500)
    bal_res2 = client.get("/api/v1/loyalty/me/balance", headers=customer_headers)
    assert bal_res2.status_code == 200
    assert bal_res2.json()["data"]["points_balance"] == 600
    assert bal_res2.json()["data"]["tier"] == "SILVER"

    # 4. Redeem 200 points ($2 discount)
    redeem_res = client.post(
        "/api/v1/loyalty/redeem",
        json={"points": 200},
        headers=customer_headers
    )
    assert redeem_res.status_code == 200
    assert redeem_res.json()["data"]["discount_amount"] == 2.0
    assert redeem_res.json()["data"]["remaining_points"] == 400

    # 5. Reverse points for cancelled order
    rev_res = client.post(
        "/api/v1/loyalty/reverse",
        json={"order_id": order.id, "reason": "Order cancelled after delivery"},
        headers=superadmin_headers
    )
    assert rev_res.status_code == 200
    assert rev_res.json()["data"]["reversed_points"] == 600
