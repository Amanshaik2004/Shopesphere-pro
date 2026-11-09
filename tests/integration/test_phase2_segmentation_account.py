import pytest
from app.models.users import User
from app.common.enums import UserStatus

def test_customer_segments_and_account_controls(client, superadmin_headers, customer_headers, db):
    prof = client.get("/api/v1/profile", headers=customer_headers).json()["data"]
    cust_id = prof["user_id"]

    # 1. Create a VIP Customer Segment
    seg_res = client.post(
        "/api/v1/customer-segments",
        json={
            "name": "High Roller VIP",
            "code": "VIP_HIGH_ROLLER",
            "description": "High value repeat shoppers",
            "min_order_count": 5,
            "min_total_spend": 2500.0,
            "purchase_limit_per_order": 10000.0
        },
        headers=superadmin_headers
    )
    assert seg_res.status_code == 200
    seg_id = seg_res.json()["data"]["id"]

    # 2. Add customer to segment
    add_mem = client.post(
        f"/api/v1/customer-segments/{seg_id}/members",
        json={"user_ids": [cust_id]},
        headers=superadmin_headers
    )
    assert add_mem.status_code == 200
    assert add_mem.json()["data"]["added_count"] == 1

    # 3. Add Customer Tag
    tag_res = client.post(
        f"/api/v1/customers/{cust_id}/tags",
        json={"tag": "preferred_electronics"},
        headers=superadmin_headers
    )
    assert tag_res.status_code == 200
    assert tag_res.json()["data"]["tag"] == "preferred_electronics"

    # 4. Add Customer Internal Note
    note_res = client.post(
        f"/api/v1/customers/{cust_id}/notes",
        json={"content": "Customer prefers morning phone calls for delivery.", "is_private": True},
        headers=superadmin_headers
    )
    assert note_res.status_code == 200
    assert "morning" in note_res.json()["data"]["content"]

    # 5. Set Account Restrictions (disable COD, set max order amount)
    rest_res = client.post(
        f"/api/v1/customers/{cust_id}/restrict",
        json={"restrictions": {"cod_allowed": False, "max_order_amount": 1000.0}},
        headers=superadmin_headers
    )
    assert rest_res.status_code == 200
    assert rest_res.json()["data"]["restrictions"]["cod_allowed"] is False

    # 6. Suspend and Reactivate Customer
    susp_res = client.post(
        f"/api/v1/customers/{cust_id}/suspend",
        json={"reason": "Suspected fraudulent activity on payment card"},
        headers=superadmin_headers
    )
    assert susp_res.status_code == 200
    assert susp_res.json()["data"]["status"] == "suspended"

    # When suspended, customer should receive 403 Forbidden on protected routes
    cust_blocked = client.get("/api/v1/profile", headers=customer_headers)
    assert cust_blocked.status_code == 403

    # Reactivate
    react_res = client.post(f"/api/v1/customers/{cust_id}/reactivate", headers=superadmin_headers)
    assert react_res.status_code == 200
    assert react_res.json()["data"]["status"] == "active"
