from app.models.users import User, Address
from app.models.orders import Order
from app.common.enums import UserRole, UserStatus, AddressType, OrderStatus
from app.core.security import hash_password, create_access_token

def test_customer_cannot_access_other_customer_address(client, customer_headers, db):
    # Create another customer
    other_user = User(
        email="other_customer@example.com",
        hashed_password=hash_password("Pass123!"),
        full_name="Other Customer",
        role=UserRole.CUSTOMER,
        status=UserStatus.ACTIVE
    )
    db.add(other_user)
    db.flush()

    other_addr = Address(
        user_id=other_user.id,
        address_type=AddressType.SHIPPING,
        full_name="Other Customer",
        phone="9999999999",
        street_address="999 Secret St",
        city="Secretville",
        state="CA",
        postal_code="90210",
        country="United States"
    )
    db.add(other_addr)
    db.commit()

    # Try to access other customer's address
    resp = client.get(f"/api/v1/addresses/{other_addr.id}", headers=customer_headers)
    assert resp.status_code == 403

def test_customer_cannot_access_other_customer_order(client, customer_headers, db):
    # Create order belonging to someone else
    other_user = db.query(User).filter(User.email == "other_customer_order@example.com").first()
    if not other_user:
        other_user = User(
            email="other_customer_order@example.com",
            hashed_password=hash_password("Pass123!"),
            full_name="Other Customer Order",
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE
        )
        db.add(other_user)
        db.flush()

    other_order = Order(
        order_number="ORD-OTHER-111",
        user_id=other_user.id,
        subtotal_amount=50.0,
        discount_amount=0.0,
        tax_amount=4.0,
        shipping_amount=5.0,
        total_amount=59.0,
        status=OrderStatus.PENDING
    )
    db.add(other_order)
    db.commit()

    resp = client.get(f"/api/v1/orders/{other_order.id}", headers=customer_headers)
    assert resp.status_code == 403
