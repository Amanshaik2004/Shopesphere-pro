import pytest
import os
import sys

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.db.base import Base
import app.db.models
from app.db.session import get_db
from app.main import app
from app.models.users import User, UserProfile
from app.models.catalog import Category, Brand, Product, ProductVariant
from app.models.inventory import Warehouse, InventoryItem
from app.models.orders import ShippingMethod, Coupon, TaxRate, Cart
from app.models.sellers import SellerProfile
from app.common.enums import UserRole, UserStatus, DiscountType, SellerStatus
from app.core.security import hash_password, create_access_token

# Use SQLite in-memory with StaticPool for ultra-fast, isolated test execution
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

@pytest.fixture
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

@pytest.fixture
def superadmin_user(db):
    user = db.query(User).filter(User.email == "superadmin_test@shopsphere.com").first()
    if not user:
        user = User(
            email="superadmin_test@shopsphere.com",
            hashed_password=hash_password("SuperAdmin123!"),
            full_name="Test SuperAdmin",
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def superadmin_token(superadmin_user):
    return create_access_token(subject=superadmin_user.id, role=superadmin_user.role.value)

@pytest.fixture
def superadmin_headers(superadmin_token):
    return {"Authorization": f"Bearer {superadmin_token}"}

@pytest.fixture
def customer_user(db):
    user = db.query(User).filter(User.email == "customer_test@shopsphere.com").first()
    if not user:
        user = User(
            email="customer_test@shopsphere.com",
            hashed_password=hash_password("Customer123!"),
            full_name="Test Customer",
            role=UserRole.CUSTOMER,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        db.add(user)
        db.flush()
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def customer_token(customer_user):
    return create_access_token(subject=customer_user.id, role=customer_user.role.value)

@pytest.fixture
def customer_headers(customer_token):
    return {"Authorization": f"Bearer {customer_token}"}

@pytest.fixture
def seller_user(db):
    user = db.query(User).filter(User.email == "seller_test@shopsphere.com").first()
    if not user:
        user = User(
            email="seller_test@shopsphere.com",
            hashed_password=hash_password("Seller123!"),
            full_name="Test Seller",
            role=UserRole.SELLER,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        db.add(user)
        db.flush()
        prof = SellerProfile(
            user_id=user.id,
            store_name="Test Seller Store",
            business_name="Test Seller Business",
            status=SellerStatus.APPROVED,
            commission_rate=10.0,
            platform_fee_percent=2.0
        )
        db.add(prof)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def seller_token(seller_user):
    return create_access_token(subject=seller_user.id, role=seller_user.role.value)

@pytest.fixture
def seller_headers(seller_token):
    return {"Authorization": f"Bearer {seller_token}"}

@pytest.fixture
def finance_user(db):
    user = db.query(User).filter(User.email == "finance_test@shopsphere.com").first()
    if not user:
        user = User(
            email="finance_test@shopsphere.com",
            hashed_password=hash_password("Finance123!"),
            full_name="Test Finance Manager",
            role=UserRole.FINANCE_MANAGER,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user

@pytest.fixture
def finance_token(finance_user):
    return create_access_token(subject=finance_user.id, role=finance_user.role.value)

@pytest.fixture
def finance_headers(finance_token):
    return {"Authorization": f"Bearer {finance_token}"}

@pytest.fixture
def sample_catalog(db):
    cat = db.query(Category).filter(Category.slug == "test-electronics").first()
    if not cat:
        cat = Category(name="Test Electronics", slug="test-electronics")
        db.add(cat)
        db.flush()

    brand = db.query(Brand).filter(Brand.slug == "test-tech").first()
    if not brand:
        brand = Brand(name="Test Tech", slug="test-tech")
        db.add(brand)
        db.flush()

    prod = db.query(Product).filter(Product.sku == "TEST-LAPTOP").first()
    if not prod:
        prod = Product(
            name="Test Laptop",
            slug="test-laptop",
            description="High performance laptop",
            category_id=cat.id,
            brand_id=brand.id,
            sku="TEST-LAPTOP",
            base_price=1000.00,
            sale_price=900.00,
            is_active=True
        )
        db.add(prod)
        db.flush()

    wh = db.query(Warehouse).filter(Warehouse.code == "TEST-WH").first()
    if not wh:
        wh = Warehouse(
            name="Test Warehouse",
            code="TEST-WH",
            address="123 Test St",
            city="Testville",
            state="TX",
            postal_code="12345"
        )
        db.add(wh)
        db.flush()

    inv = db.query(InventoryItem).filter(InventoryItem.product_id == prod.id, InventoryItem.warehouse_id == wh.id).first()
    if not inv:
        inv = InventoryItem(
            product_id=prod.id,
            warehouse_id=wh.id,
            quantity=50,
            reserved_quantity=0,
            low_stock_threshold=5
        )
        db.add(inv)
        db.flush()

    ship = db.query(ShippingMethod).filter(ShippingMethod.name == "Standard").first()
    if not ship:
        ship = ShippingMethod(
            name="Standard",
            carrier="DHL",
            base_cost=10.00,
            free_shipping_threshold=1500.00
        )
        db.add(ship)
        db.flush()

    db.commit()
    return {"category": cat, "brand": brand, "product": prod, "warehouse": wh, "inventory": inv, "shipping": ship}
