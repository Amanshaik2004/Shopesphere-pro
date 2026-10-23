from app.models.users import Address
from app.common.enums import AddressType

def test_cart_and_checkout_flow(client, customer_headers, customer_user, sample_catalog, db):
    # Add address for customer
    addr = Address(
        user_id=customer_user.id,
        address_type=AddressType.SHIPPING,
        full_name="John Doe",
        phone="1234567890",
        street_address="456 Elm St",
        city="Austin",
        state="TX",
        postal_code="78701",
        country="United States",
        is_default=True
    )
    db.add(addr)
    db.commit()
    db.refresh(addr)

    # 1. Add item to cart (quantity 1, subtotal 900 < free shipping threshold 1500)
    prod = sample_catalog["product"]
    resp = client.post("/api/v1/cart/items", json={
        "product_id": prod.id,
        "quantity": 1
    }, headers=customer_headers)
    assert resp.status_code == 200
    cart_data = resp.json()["data"]
    assert len(cart_data["items"]) == 1
    assert cart_data["subtotal"] > 0

    # 2. Calculate cart price
    ship = sample_catalog["shipping"]
    calc_resp = client.post("/api/v1/cart/calculate", json={
        "shipping_method_id": ship.id,
        "country": "United States"
    }, headers=customer_headers)
    assert calc_resp.status_code == 200
    calc_data = calc_resp.json()["data"]
    assert calc_data["shipping_amount"] == 10.0

    # 3. Checkout
    checkout_resp = client.post("/api/v1/checkout", json={
        "shipping_address_id": addr.id,
        "shipping_method_id": ship.id,
        "payment_method": "stripe"
    }, headers=customer_headers)
    assert checkout_resp.status_code == 200
    order_data = checkout_resp.json()["data"]
    assert "order_number" in order_data
    assert order_data["status"] == "pending"
