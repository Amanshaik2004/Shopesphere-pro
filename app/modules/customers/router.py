from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User, UserProfile
from app.models.orders import Cart
from app.core.security import hash_password
from app.core.exceptions import ConflictError, NotFoundError
from app.common.responses import ResponseSchema, MessageResponse
from app.common.enums import UserRole, UserStatus
from app.modules.customers.schemas import CustomerRegisterRequest, CustomerRegisterResponse, VerifyEmailRequest

router = APIRouter(prefix="/customers", tags=["Module 03: Customer Registration"])

@router.post("/register", response_model=ResponseSchema[CustomerRegisterResponse])
def register_customer(data: CustomerRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise ConflictError("A customer with this email address already exists")
    
    user = User(
        email=data.email,
        hashed_password=hash_password(data.password),
        full_name=data.full_name,
        phone_number=data.phone_number,
        role=UserRole.CUSTOMER,
        status=UserStatus.ACTIVE,
        email_verified=False
    )
    db.add(user)
    db.flush()
    
    # Initialize profile and shopping cart
    profile = UserProfile(user_id=user.id)
    cart = Cart(user_id=user.id)
    db.add(profile)
    db.add(cart)
    db.commit()
    db.refresh(user)
    
    return ResponseSchema(
        message="Customer registration successful. Please verify your email.",
        data=CustomerRegisterResponse.model_validate(user)
    )

@router.post("/verify-email", response_model=ResponseSchema[MessageResponse])
def verify_email(data: VerifyEmailRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.token_or_email).first()
    if not user:
        raise NotFoundError("User not found with provided email")
    
    user.email_verified = True
    db.commit()
    return ResponseSchema(
        message="Email successfully verified",
        data=MessageResponse(message="Email verified. Account is now in verified state.")
    )
