from app.models.orders import Coupon
from app.common.enums import DiscountType
from datetime import datetime, timezone, timedelta

def test_full_shopping_lifecycle(client, sample_catalog, superadmin_headers, db):
    # 1. Register new customer
    reg_resp = client.post("/api/v1/customers/register", json={
        "email": "shopping_user@example.com",
        "password": "Password123!",
        "full_name": "Alice Shopper",
        "phone_number": "5551234567"
    })
    assert reg_resp.status_code == 200

    # 2. Login
    login_resp = client.post("/api/v1/auth/login", json={
        "email": "shopping_user@example.com",
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["data"]["access_token"]
    user_headers = {"Authorization": f"Bearer {token}"}

    # 3. Add address
    addr_resp = client.post("/api/v1/addresses", json={
        "full_name": "Alice Shopper",
        "phone": "5551234567",
        "street_address": "123 Shopping Lane",
        "city": "Austin",
        "state": "TX",
        "postal_code": "78701",
        "country": "United States",
        "is_default": True
    }, headers=user_headers)
    assert addr_resp.status_code == 200
    addr_id = addr_resp.json()["data"]["id"]

    # 4. Add product to cart
    prod = sample_catalog["product"]
    cart_resp = client.post("/api/v1/cart/items", json={
        "product_id": prod.id,
        "quantity": 1
    }, headers=user_headers)
    assert cart_resp.status_code == 200

    # 5. Checkout
    ship = sample_catalog["shipping"]
    checkout_resp = client.post("/api/v1/checkout", json={
        "shipping_address_id": addr_id,
        "shipping_method_id": ship.id,
        "payment_method": "stripe"
    }, headers=user_headers)
    assert checkout_resp.status_code == 200
    order_data = checkout_resp.json()["data"]
    order_id = order_data["order_id"]
    assert order_data["status"] == "pending"

    # 6. Process payment
    pay_resp = client.post("/api/v1/payments/process", json={
        "order_id": order_id,
        "payment_method": "stripe"
    }, headers=user_headers)
    assert pay_resp.status_code == 200
    assert pay_resp.json()["data"]["status"] == "successful"

    # 7. Create shipment (as staff)
    ship_resp = client.post("/api/v1/shipments", json={
        "order_id": order_id,
        "carrier": "Standard Express"
    }, headers=superadmin_headers)
    assert ship_resp.status_code == 200
    shipment_id = ship_resp.json()["data"]["id"]
    tracking_num = ship_resp.json()["data"]["tracking_number"]

    # 8. Add dispatch tracking event
    track_resp = client.post("/api/v1/tracking/events", json={
        "shipment_id": shipment_id,
        "status": "dispatched",
        "location": "Dallas Hub",
        "description": "Package in transit"
    }, headers=superadmin_headers)
    assert track_resp.status_code == 200

    # 9. Deliver package
    deliv_resp = client.post(f"/api/v1/deliveries/{shipment_id}/attempt", json={
        "is_successful": True,
        "confirmation_signature": "Alice Shopper"
    }, headers=superadmin_headers)
    assert deliv_resp.status_code == 200

    # Verify order is delivered
    order_resp = client.get(f"/api/v1/orders/{order_id}", headers=user_headers)
    assert order_resp.status_code == 200
    assert order_resp.json()["data"]["status"] == "delivered"
