import pytest
from app.models.orders import Order, OrderItem
from app.models.catalog import Product
from app.common.enums import OrderStatus, SellerStatus, SettlementStatus

def test_seller_onboarding_and_product_management(client, customer_headers, seller_headers, superadmin_headers, sample_catalog, db):
    cat = sample_catalog["category"]

    # 1. Customer onboards as seller
    onboard_resp = client.post(
        "/api/v1/sellers/onboard",
        json={
            "store_name": "Apex Tech Direct",
            "business_name": "Apex Technologies LLC",
            "business_registration": "REG-TX-998877",
            "bank_account_info": "IBAN-US-123456789"
        },
        headers=customer_headers
    )
    assert onboard_resp.status_code == 200
    seller_id = onboard_resp.json()["data"]["id"]
    assert onboard_resp.json()["data"]["status"] == "PENDING"

    # 2. Superadmin reviews and approves seller with 12% commission
    rev_resp = client.put(
        f"/api/v1/sellers/{seller_id}/review",
        json={
            "status": SellerStatus.APPROVED,
            "commission_rate": 12.0,
            "platform_fee_percent": 2.0
        },
        headers=superadmin_headers
    )
    assert rev_resp.status_code == 200
    assert rev_resp.json()["data"]["status"] == "APPROVED"
    assert rev_resp.json()["data"]["commission_rate"] == 12.0

    # 3. Seller creates marketplace product
    prod_resp = client.post(
        "/api/v1/sellers/products",
        json={
            "name": "Apex Wireless Gaming Mouse",
            "slug": "apex-wireless-gaming-mouse",
            "description": "Ergonomic 24000 DPI gaming mouse",
            "category_id": cat.id,
            "sku": "APEX-MOUSE-01",
            "base_price": 100.0,
            "sale_price": 80.0
        },
        headers=seller_headers
    )
    assert prod_resp.status_code == 200
    seller_prod_id = prod_resp.json()["data"]["id"]

    # 4. Seller lists their products
    my_prods = client.get("/api/v1/sellers/products", headers=seller_headers)
    assert my_prods.status_code == 200
    assert any(p["id"] == seller_prod_id for p in my_prods.json()["data"])


def test_seller_orders_settlement_and_summary(client, seller_headers, superadmin_headers, finance_headers, sample_catalog, db):
    # Get seller user id
    seller_prof = client.get("/api/v1/sellers/profile", headers=seller_headers).json()["data"]
    seller_uid = seller_prof["user_id"]

    prod = sample_catalog["product"]
    prod.seller_id = seller_uid
    db.commit()

    order = Order(
        order_number="ORD-SELLER-SETTLE-001",
        user_id=1,
        subtotal_amount=900.0,
        discount_amount=0.0,
        tax_amount=0.0,
        shipping_amount=0.0,
        total_amount=900.0,
        status=OrderStatus.CONFIRMED
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
        fulfillment_status="PENDING"
    )
    db.add(item)
    db.commit()

    # 1. Seller views their order items
    seller_orders = client.get("/api/v1/sellers/orders", headers=seller_headers)
    assert seller_orders.status_code == 200
    assert len(seller_orders.json()["data"]) >= 1

    # 2. Seller fulfills item
    fulf_res = client.post(f"/api/v1/sellers/order-items/{item.id}/fulfill", headers=seller_headers)
    assert fulf_res.status_code == 200
    assert fulf_res.json()["data"]["fulfillment_status"] == "FULFILLED"

    # 3. Finance generates settlement
    gen_res = client.post(f"/api/v1/sellers/settlements/generate?order_id={order.id}", headers=finance_headers)
    assert gen_res.status_code == 200
    settlements = gen_res.json()["data"]
    assert len(settlements) >= 1
    settle = settlements[0]
    settle_id = settle["id"]
    # Gross: 900, 10% comm = 90, 2% fee = 18 -> net = 792.0
    assert settle["gross_amount"] == 900.0
    assert settle["commission_amount"] == 90.0
    assert settle["platform_fee"] == 18.0
    assert settle["net_amount"] == 792.0

    # 4. Finance marks payout
    pay_res = client.post(f"/api/v1/sellers/settlements/{settle_id}/payout", headers=finance_headers)
    assert pay_res.status_code == 200
    assert pay_res.json()["data"]["status"] == "SETTLED"

    # 5. Seller views sales summary
    sum_res = client.get("/api/v1/sellers/sales-summary", headers=seller_headers)
    assert sum_res.status_code == 200
    assert sum_res.json()["data"]["net_earnings"] >= 792.0
