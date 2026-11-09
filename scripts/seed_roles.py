import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.db.session import SessionLocal
from app.models.users import User, UserProfile
from app.models.sellers import SellerProfile
from app.common.enums import UserRole, UserStatus, SellerStatus
from app.core.security import hash_password

STAFF_ACCOUNTS = [
    ("superadmin@shopsphere.com", "Super Administrator", UserRole.SUPER_ADMIN, "SuperAdmin123!"),
    ("admin@shopsphere.com", "Platform Admin", UserRole.ADMIN, "Password123!"),
    ("productmanager@shopsphere.com", "Product Manager", UserRole.PRODUCT_MANAGER, "Password123!"),
    ("inventorymanager@shopsphere.com", "Inventory Manager", UserRole.INVENTORY_MANAGER, "Password123!"),
    ("ordermanager@shopsphere.com", "Order Manager", UserRole.ORDER_MANAGER, "Password123!"),
    ("supportagent@shopsphere.com", "Support Agent", UserRole.SUPPORT_AGENT, "Password123!"),
    ("deliverymanager@shopsphere.com", "Delivery Manager", UserRole.DELIVERY_MANAGER, "Password123!"),
    ("financemanager@shopsphere.com", "Finance Manager", UserRole.FINANCE_MANAGER, "Password123!"),
    ("customer@shopsphere.com", "John Doe Customer", UserRole.CUSTOMER, "Password123!"),
    ("seller@shopsphere.com", "Acme Merchant Seller", UserRole.SELLER, "Password123!")
]

def seed_roles():
    db = SessionLocal()
    try:
        for email, name, role, pwd in STAFF_ACCOUNTS:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                user = User(
                    email=email,
                    hashed_password=hash_password(pwd),
                    full_name=name,
                    role=role,
                    status=UserStatus.ACTIVE,
                    email_verified=True
                )
                db.add(user)
                db.flush()
                profile = UserProfile(user_id=user.id, bio=f"Role: {role.value}")
                db.add(profile)
                if role == UserRole.SELLER:
                    seller_prof = SellerProfile(
                        user_id=user.id,
                        store_name="Acme Official",
                        business_name="Acme Global Inc",
                        status=SellerStatus.APPROVED,
                        commission_rate=10.0,
                        platform_fee_percent=2.0
                    )
                    db.add(seller_prof)
                print(f"Created {role.value}: {email}")
            else:
                print(f"User {email} already exists")
        db.commit()
        print("Role seeding complete!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_roles()
