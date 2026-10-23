from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.users import User, RevokedToken, UserActivity
from app.core.security import verify_password, hash_password, create_access_token, create_refresh_token, decode_token
from app.core.exceptions import UnauthorizedError, BadRequestError
from app.common.responses import ResponseSchema, MessageResponse
from app.common.dependencies import get_current_user, get_current_active_user
from app.common.enums import UserStatus, AuditAction
from app.core.audit import log_audit
from app.modules.authentication.schemas import LoginRequest, TokenResponse, RefreshTokenRequest, PasswordChangeRequest, LogoutRequest

router = APIRouter(prefix="/auth", tags=["Module 01: Authentication & Authorization"])

@router.post("/login", response_model=ResponseSchema[TokenResponse])
def login(login_data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()
    if not user or not verify_password(login_data.password, user.hashed_password):
        raise UnauthorizedError("Invalid email or password")
    
    if user.status != UserStatus.ACTIVE:
        raise UnauthorizedError(f"Account is {user.status.value}. Please contact support.")
    
    user.last_login_at = datetime.now(timezone.utc)
    
    # Record activity
    ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    activity = UserActivity(user_id=user.id, action="LOGIN", ip_address=ip, user_agent=user_agent)
    db.add(activity)
    db.commit()
    
    access_token = create_access_token(subject=user.id, role=user.role.value)
    refresh_token = create_refresh_token(subject=user.id, role=user.role.value)
    
    log_audit(db, AuditAction.AUTH_LOGIN, "User", entity_id=str(user.id), user_id=user.id, ip_address=ip)
    
    return ResponseSchema(
        message="Login successful",
        data=TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            role=user.role.value,
            user_id=user.id,
            full_name=user.full_name
        )
    )

@router.post("/refresh", response_model=ResponseSchema[TokenResponse])
def refresh_token(payload_in: RefreshTokenRequest, db: Session = Depends(get_db)):
    payload = decode_token(payload_in.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise UnauthorizedError("Invalid or expired refresh token")
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user or user.status != UserStatus.ACTIVE:
        raise UnauthorizedError("User is no longer active")
    
    new_access_token = create_access_token(subject=user.id, role=user.role.value)
    new_refresh_token = create_refresh_token(subject=user.id, role=user.role.value)
    
    return ResponseSchema(
        message="Token refreshed successfully",
        data=TokenResponse(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            role=user.role.value,
            user_id=user.id,
            full_name=user.full_name
        )
    )

@router.post("/logout", response_model=ResponseSchema[MessageResponse])
def logout(
    request: Request,
    authorization: str = Header(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        revoked = RevokedToken(
            token=token,
            user_id=current_user.id,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        db.add(revoked)
        
        ip = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        activity = UserActivity(user_id=current_user.id, action="LOGOUT", ip_address=ip, user_agent=user_agent)
        db.add(activity)
        db.commit()
        
        log_audit(db, AuditAction.AUTH_LOGOUT, "User", entity_id=str(current_user.id), user_id=current_user.id, ip_address=ip)
        
    return ResponseSchema(message="Logged out successfully", data=MessageResponse(message="Token successfully invalidated"))

@router.post("/change-password", response_model=ResponseSchema[MessageResponse])
def change_password(
    data: PasswordChangeRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    if not verify_password(data.old_password, current_user.hashed_password):
        raise BadRequestError("Current password does not match")
    if len(data.new_password) < 6:
        raise BadRequestError("New password must be at least 6 characters")
    
    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return ResponseSchema(message="Password changed successfully", data=MessageResponse(message="Password updated successfully"))
