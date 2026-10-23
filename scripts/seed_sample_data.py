import sys
import os
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import SessionLocal
import app.db.models
from app.models.catalog import Category, Brand, Product, ProductVariant
from app.models.inventory import Warehouse, InventoryItem
from app.models.orders import ShippingMethod, Coupon, TaxRate
from app.models.suppliers import Supplier
from app.common.enums import DiscountType

def seed_sample_data():
    db = SessionLocal()
    try:
        # Categories
        cat_elec = db.query(Category).filter(Category.slug == "electronics").first()
        if not cat_elec:
            cat_elec = Category(name="Electronics", slug="electronics", description="Gadgets and tech")
            db.add(cat_elec)
            db.flush()

        cat_apparel = db.query(Category).filter(Category.slug == "apparel").first()
        if not cat_apparel:
            cat_apparel = Category(name="Apparel", slug="apparel", description="Fashion clothing")
            db.add(cat_apparel)
            db.flush()

        # Brands
        brand_apple = db.query(Brand).filter(Brand.slug == "apple").first()
        if not brand_apple:
            brand_apple = Brand(name="Apple", slug="apple", website="https://apple.com")
            db.add(brand_apple)
            db.flush()

        brand_nike = db.query(Brand).filter(Brand.slug == "nike").first()
        if not brand_nike:
            brand_nike = Brand(name="Nike", slug="nike", website="https://nike.com")
            db.add(brand_nike)
            db.flush()

        # Warehouses
        wh1 = db.query(Warehouse).filter(Warehouse.code == "WH-MAIN").first()
        if not wh1:
            wh1 = Warehouse(
                name="Central Fulfillment Center",
                code="WH-MAIN",
                address="100 Logistics Blvd",
                city="Dallas",
                state="TX",
                postal_code="75001",
                capacity=50000
            )
            db.add(wh1)
            db.flush()

        wh2 = db.query(Warehouse).filter(Warehouse.code == "WH-WEST").first()
        if not wh2:
            wh2 = Warehouse(
                name="West Coast Hub",
                code="WH-WEST",
                address="200 Harbor Way",
                city="Los Angeles",
                state="CA",
                postal_code="90001",
                capacity=30000
            )
            db.add(wh2)
            db.flush()

        # Products
        p1 = db.query(Product).filter(Product.sku == "IPHONE15-PRO").first()
        if not p1:
            p1 = Product(
                name="iPhone 15 Pro Max",
                slug="iphone-15-pro-max",
                description="Latest flagship smartphone with titanium design.",
                category_id=cat_elec.id,
                brand_id=brand_apple.id,
                sku="IPHONE15-PRO",
                base_price=1199.99,
                sale_price=1099.99,
                is_active=True,
                is_featured=True
            )
            db.add(p1)
            db.flush()

            # Variants
            v1 = ProductVariant(product_id=p1.id, sku="IPHONE15-PRO-256-BLK", name="256GB Black", color="Black", additional_price=0.0)
            v2 = ProductVariant(product_id=p1.id, sku="IPHONE15-PRO-512-NAT", name="512GB Natural", color="Natural", additional_price=200.0)
            db.add(v1)
            db.add(v2)
            db.flush()

            # Stock in WH1
            inv1 = InventoryItem(product_id=p1.id, variant_id=v1.id, warehouse_id=wh1.id, quantity=100, low_stock_threshold=10)
            inv2 = InventoryItem(product_id=p1.id, variant_id=v2.id, warehouse_id=wh1.id, quantity=50, low_stock_threshold=5)
            db.add(inv1)
            db.add(inv2)

        # Shipping Methods
        sm1 = db.query(ShippingMethod).filter(ShippingMethod.name == "Standard Express").first()
        if not sm1:
            sm1 = ShippingMethod(
                name="Standard Express",
                carrier="UPS",
                base_cost=15.00,
                free_shipping_threshold=100.00,
                estimated_days_min=3,
                estimated_days_max=5
            )
            db.add(sm1)

        sm2 = db.query(ShippingMethod).filter(ShippingMethod.name == "Next Day Priority").first()
        if not sm2:
            sm2 = ShippingMethod(
                name="Next Day Priority",
                carrier="FedEx",
                base_cost=35.00,
                free_shipping_threshold=None,
                estimated_days_min=1,
                estimated_days_max=1
            )
            db.add(sm2)

        # Coupons
        now = datetime.now(timezone.utc)
        c1 = db.query(Coupon).filter(Coupon.code == "WELCOME20").first()
        if not c1:
            c1 = Coupon(
                code="WELCOME20",
                discount_type=DiscountType.PERCENTAGE,
                discount_value=20.0,
                min_purchase_amount=50.0,
                max_discount_amount=100.0,
                valid_from=now - timedelta(days=1),
                valid_to=now + timedelta(days=365)
            )
            db.add(c1)

        # Tax
        t1 = db.query(TaxRate).filter(TaxRate.name == "US Standard Tax").first()
        if not t1:
            t1 = TaxRate(
                name="US Standard Tax",
                rate_percentage=8.25,
                country="United States"
            )
            db.add(t1)

        # Supplier
        sup = db.query(Supplier).filter(Supplier.name == "TechSource Global Ltd").first()
        if not sup:
            sup = Supplier(
                name="TechSource Global Ltd",
                contact_person="Alice Smith",
                email="alice@techsource.com",
                phone="+1-800-555-0199",
                address="77 Industrial Way, Silicon Valley, CA"
            )
            db.add(sup)

        db.commit()
        print("Sample data successfully seeded!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_sample_data()
