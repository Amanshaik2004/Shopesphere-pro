from datetime import datetime, timezone, timedelta
from app.models.orders import Coupon, Promotion
from app.models.segmentation import CustomerSegment, CustomerSegmentMember
from app.common.enums import DiscountType, PromotionType

def test_coupon_validation_api(client, superadmin_headers, db):
    now = datetime.now(timezone.utc)
    # 1. Valid coupon
    c1 = Coupon(
        code="SAVE20PERCENT",
        discount_type=DiscountType.PERCENTAGE,
        discount_value=20.0,
        min_purchase_amount=100.0,
        max_discount_amount=50.0,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=10),
        is_active=True
    )
    db.add(c1)

    # 2. Expired coupon
    c2 = Coupon(
        code="EXPIRED50",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=50.0,
        min_purchase_amount=50.0,
        valid_from=now - timedelta(days=10),
        valid_to=now - timedelta(days=1),
        is_active=True
    )
    db.add(c2)
    db.commit()

    # Validate c1 with cart 200: 20% of 200 = 40 (<= cap 50)
    res1 = client.post("/api/v1/coupons/validate", json={"code": "save20percent", "cart_amount": 200.0})
    assert res1.status_code == 200
    d1 = res1.json()["data"]
    assert d1["is_valid"] is True
    assert d1["discount_amount"] == 40.0

    # Validate c1 with cart 50: below min purchase 100
    res_min = client.post("/api/v1/coupons/validate", json={"code": "save20percent", "cart_amount": 50.0})
    assert res_min.status_code == 200
    assert res_min.json()["data"]["is_valid"] is False

    # Validate c2: expired
    res2 = client.post("/api/v1/coupons/validate", json={"code": "expired50", "cart_amount": 200.0})
    assert res2.status_code == 200
    assert res2.json()["data"]["is_valid"] is False


def test_comprehensive_price_breakdown(client, sample_catalog, db):
    prod = sample_catalog["product"]
    now = datetime.now(timezone.utc)

    # Add product promotion: 10% off
    promo_prod = Promotion(
        name="10% Off Laptop",
        promotion_type=PromotionType.PRODUCT,
        discount_type=DiscountType.PERCENTAGE,
        discount_value=10.0,
        product_id=prod.id,
        start_date=now - timedelta(days=1),
        end_date=now + timedelta(days=10),
        is_active=True
    )
    db.add(promo_prod)

    # Add coupon
    coupon = Coupon(
        code="BONUS50",
        discount_type=DiscountType.FIXED_AMOUNT,
        discount_value=50.0,
        min_purchase_amount=500.0,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=10),
        is_active=True
    )
    db.add(coupon)
    db.commit()

    # Request price breakdown for 1 unit of product ($900 sale price)
    resp = client.post(
        "/api/v1/pricing/price-breakdown",
        json={
            "items": [{"product_id": prod.id, "quantity": 1}],
            "coupon_code": "BONUS50"
        }
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["subtotal_amount"] == 900.0
    # 10% of 900 = 90
    assert data["product_promotions_discount"] == 90.0
    # Coupon bonus: 50
    assert data["coupon_discount"] == 50.0
    assert data["total_discount"] == 140.0
    # Net subtotal = 760; tax 5% = 38.0; shipping 0 (>= 100); total = 798.0
    assert data["tax_amount"] == 38.0
    assert data["total_amount"] == 798.0
    assert len(data["applied_promotions"]) >= 2
