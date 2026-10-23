from sqlalchemy.orm import Session
from app.db.models import Base
from app.db.session import engine, SessionLocal
from app.models.users import User, UserProfile
from app.common.enums import UserRole, UserStatus
from app.core.security import hash_password
from app.core.config import settings
from app.core.logging import logger

def init_db(db: Session) -> None:
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Check if super admin exists
    admin = db.query(User).filter(User.email == settings.SUPER_ADMIN_EMAIL).first()
    if not admin:
        logger.info(f"Creating super admin: {settings.SUPER_ADMIN_EMAIL}")
        admin = User(
            email=settings.SUPER_ADMIN_EMAIL,
            hashed_password=hash_password(settings.SUPER_ADMIN_PASSWORD),
            full_name=settings.SUPER_ADMIN_FULL_NAME,
            role=UserRole.SUPER_ADMIN,
            status=UserStatus.ACTIVE,
            email_verified=True
        )
        db.add(admin)
        db.flush()
        
        profile = UserProfile(user_id=admin.id, bio="Master Super Administrator for ShopSphere Pro")
        db.add(profile)
        db.commit()
        logger.info("Super admin created successfully.")
